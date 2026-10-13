/* d3d9.dll 代理 + 文件路径代码页修复
 *
 * 背景：LEGO Indiana Jones 2 是 2009 年的非 Unicode 程序，只用 ANSI 文件 API
 * （CreateFileA/CreateDirectoryA/FindFirstFileA 等），且 exe 硬编码了 CP1252/1254
 * 编码的存档目录名 "LEGO® Indiana Jones™ 2"（®=0xAE, ™=0x99）。
 * 在中文系统（GBK/CP936）下，这些字节被内核转成 '?'（非法文件名）→ 存档失败跳出。
 *
 * 本 DLL 通过 IAT hook 拦截这些 A 版 API，把路径按 CP1254 转成 Unicode 后调 W 版，
 * 从而绕过内核的 GBK 转换。纯 ASCII 路径在 CP1254 下映射不变，故对其它路径无副作用。
 *
 * 导出策略（关键）：游戏原版目录里**没有** d3d9.dll，本 DLL 是靠文件名劫持被加载的，
 * 所以它必须把 d3d9 的 17 个导出**自己实现**出来。不能像以前那样转发到
 * d3d9_orig.dll —— 那要求分发包里必须额外附带一份系统 d3d9 的副本，
 * 而那份副本的版本被硬钉在打包者电脑上（实测 v0.0.26100.9587 = Win11 24H2），
 * 别人机器上若是 Win10 或更早的 d3d9 就直接加载失败，且症状与"文件缺失"一模一样。
 *
 * 现在改为运行时自己定位系统目录（GetSystemDirectoryW，32 位进程在 64 位系统上
 * 自动返回 SysWOW64，正好是我们要的），拼出 \d3d9.dll 加载，再转发过去。
 * 这样游戏目录里只需一个 d3d9.dll，跨 Windows 版本自适应。
 */
#include <windows.h>
#include <stdlib.h>
#include <string.h>
#include "ui_patch.h"

/* ------------------------------------------------------------------ 原函数指针 */
typedef HANDLE (WINAPI *CreateFileA_t)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef BOOL (WINAPI *CreateDirectoryA_t)(LPCSTR, LPSECURITY_ATTRIBUTES);
typedef BOOL (WINAPI *DeleteFileA_t)(LPCSTR);
typedef BOOL (WINAPI *RemoveDirectoryA_t)(LPCSTR);
typedef DWORD (WINAPI *GetFileAttributesA_t)(LPCSTR);
typedef BOOL (WINAPI *SetFileAttributesA_t)(LPCSTR, DWORD);
typedef BOOL (WINAPI *MoveFileA_t)(LPCSTR, LPCSTR);
typedef HANDLE (WINAPI *FindFirstFileA_t)(LPCSTR, LPWIN32_FIND_DATAA);
typedef BOOL (WINAPI *FindNextFileA_t)(HANDLE, LPWIN32_FIND_DATAA);
typedef BOOL (WINAPI *CopyFileA_t)(LPCSTR, LPCSTR, BOOL);

static CreateFileA_t RealCreateFileA;
static CreateDirectoryA_t RealCreateDirectoryA;
static DeleteFileA_t RealDeleteFileA;
static RemoveDirectoryA_t RealRemoveDirectoryA;
static GetFileAttributesA_t RealGetFileAttributesA;
static SetFileAttributesA_t RealSetFileAttributesA;
static MoveFileA_t RealMoveFileA;
static FindFirstFileA_t RealFindFirstFileA;
static FindNextFileA_t RealFindNextFileA;
static CopyFileA_t RealCopyFileA;

/* ==================================================================== 转发层
 *
 * 下面这一段是本次改造的主体：把 d3d9.dll 的 17 个导出自己实现出来，
 * 运行时去系统目录找真正的 d3d9.dll 并转发。
 *
 * 签名说明（重要）：不引 d3d9.h，全部按 DWORD 槽位透传。
 * x86 stdcall 下每个参数都占 4 字节栈槽、返回值也占 4 字节，
 * 所以「几个 4 字节槽进、几个 4 字节槽出」对齐了，栈就不会失衡。
 * 参数个数是**实测**出来的（probe_sig.exe 扫系统 d3d9 各导出机器码里的
 * `ret imm16`，imm16/4 = stdcall 参数个数），不是照抄 MSDN ——
 * MSDN 上 PSGPSampleTexture / PSGPError / DebugSetMute 都写着有参数，
 * 但零售版 d3d9 里它们是无参空实现。抄文档会导致栈失衡直接崩游戏。
 */
typedef long (WINAPI *pfn0_t)(void);
typedef long (WINAPI *pfn1_t)(DWORD);
typedef long (WINAPI *pfn2_t)(DWORD, DWORD);
typedef long (WINAPI *pfn3_t)(DWORD, DWORD, DWORD);
typedef long (WINAPI *pfn4_t)(DWORD, DWORD, DWORD, DWORD);

static pfn0_t F_D3DPERF_EndEvent, F_D3DPERF_GetStatus, F_D3DPERF_QueryRepeatFrame;
static pfn0_t F_DebugSetLevel, F_DebugSetMute;
static pfn0_t F_PSGPError, F_PSGPSampleTexture;
static pfn1_t F_D3DPERF_SetOptions, F_Direct3D9EnableMaximizedWindowedModeShim, F_Direct3DCreate9;
static pfn2_t F_D3DPERF_BeginEvent, F_D3DPERF_SetMarker, F_D3DPERF_SetRegion, F_Direct3DCreate9Ex;
static pfn3_t F_Direct3DCreate9On12;
static pfn4_t F_Direct3DCreate9On12Ex;

static HMODULE g_real;              /* 系统 d3d9.dll 句柄 */
static volatile LONG g_state;       /* 0=未初始化 1=成功 2=失败 */

/* 只用纯 ASCII —— 报错时不能依赖任何中文字体/编码。
 * step 必须真的显示出来：上一版把参数 (void)what 丢掉了，弹出的框里
 * "Failed step:" 后面是空的，等于白报。这里用 wsprintfA 拼进正文，
 * 并带上 GetLastError()，否则 LoadLibraryW 失败时无从区分是文件不存在、
 * 依赖缺失还是位数不对。 */
static void fatal(const char* what) {
    char body[512];
    wsprintfA(body,
              "d3d9 proxy: cannot bind system d3d9.dll\n\n"
              "Step   : %s\n"
              "WinErr : %lu (0x%08lX)\n\n"
              "The proxy DLL in the game folder could not load the real\n"
              "d3d9.dll from the Windows system directory.",
              what, (unsigned long)GetLastError(),
              (unsigned long)GetLastError());
    MessageBoxA(NULL, body, "d3d9 proxy - bind failed", MB_OK | MB_ICONERROR);
    ExitProcess(0xC0000135);         /* STATUS_DLL_NOT_FOUND，与缺 DLL 表现一致 */
}

/* 定位系统里的 **32 位** d3d9.dll。
 *
 * 踩过的坑（实测 Win11 24H2 + 32 位进程）：
 * GetSystemDirectoryW 返回 C:/Windows/system32，里面躺的是 **64 位** 的
 * d3d9.dll（1774824 B）。直接加载它，游戏随后调 Direct3DCreate9 会因位数不符
 * 而失败。位数不符时报的是ERROR_BAD_EXE_FORMAT(193)，不报缺导出，
 * 但两者的修法完全不同，值得分开说明。
 *
 * 实测两个文件不同：
 *   C:/Windows/SysWOW64/d3d9.dll  1528608 B  32 位  17 个导出齐全
 *   C:/Windows/System32/d3d9.dll  1774824 B  64 位  只有 16 个（缺上面那个）
 *
 * 所以按 IsWow64Process 分流：
 *   64 位系统 -> System32 换成 SysWOW64，拿 32 位那份
 *   32 位系统 -> System32 里本来就是 32 位，直接用
 * IsWow64Process 在真的 32 位系统上返回 FALSE 且不设错误码，
 * 因此"不是 Wow64"和"真 32 位系统"可以合并成同一分支。
 * 动态取它是为了不把这个符号写进导入表 —— 否则在 32 位系统上加载就失败。 */
static HMODULE load_system_d3d9(void) {
    WCHAR dir[MAX_PATH];
    UINT n = GetSystemDirectoryW(dir, MAX_PATH);
    if (n == 0 || n >= MAX_PATH - 12) { SetLastError(ERROR_INSUFFICIENT_BUFFER); return NULL; }

    typedef BOOL (WINAPI *IsWow64Process_t)(HANDLE, PBOOL);
    IsWow64Process_t pIsWow64 =
        (IsWow64Process_t)GetProcAddress(GetModuleHandleA("kernel32.dll"), "IsWow64Process");
    if (!pIsWow64) { SetLastError(ERROR_PROC_NOT_FOUND); return NULL; }

    BOOL wow64 = FALSE;
    if (!pIsWow64(GetCurrentProcess(), &wow64)) return NULL;

    if (wow64) {
        /* 把末尾的 \system32 换成 \SysWOW64，保留前缀（通常就是 C:/Windows） */
        WCHAR* tail = NULL;
        UINT i;
        for (i = n; i > 0; i--) {
            if (dir[i - 1] == L'\\') { tail = dir + i - 1; break; }
        }
        if (!tail) { SetLastError(ERROR_PATH_NOT_FOUND); return NULL; }

        size_t prefix = (size_t)(tail - dir) + 1;   /* 含末尾的 '\' */
        static const WCHAR kWow[] = L"SysWOW64";
        const size_t kWowLen = 8;
        if (prefix + kWowLen + 10 >= MAX_PATH) {   /* +10 留给 "\d3d9.dll" 与 NUL */
            SetLastError(ERROR_INSUFFICIENT_BUFFER);
            return NULL;
        }
        /* 必须先写NUL 截断：不截的话 dir 里 "system32" 的尾巴还在，
         * memcpy 覆盖 8 个字符后剩下的残字节会拼出 "SysWOm32" 这种
         * 看似合理、实则不存在的路径，LoadLibraryW 报 126 却毫无线索。 */
        dir[prefix] = 0;
        memcpy(dir + prefix, kWow, kWowLen * sizeof(WCHAR));
        dir[prefix + kWowLen] = 0;
        n = (UINT)(prefix + kWowLen);
    }

    lstrcatW(dir, L"\\d3d9.dll");
    return LoadLibraryW(dir);
}

/* ============================================================ 设置菜单标签汉化
 *
 * 背景：菜单上的英文（Video Settings / Screen Resolution / Back …）
 * 不在 DAT 里 —— text.csv 早就全汉化了。这些标签硬编码在 exe 的 .rdata，
 * 原地改内容零余量，改exe 文件又会触发 Steam DRM。
 *
 * 解法：exe 的 .data 节里有一张多语言 UI 字符串**指针表**，
 * 每项 4 字节，指向 .rdata 里的实际字符串。表分四段，挤在一起：
 *
 *   0xAB09F0..0xAB0B48  cvar 名（pcconfig.txt 的键名）—— 绝对不碰
 *   0xAB0B5C..0xAB0C24  英文 UI（主菜单）              —— 目标
 *   0xAB0CA4..0xAB0D24  英文 UI（Builder 菜单副本）   —— 目标
 *   0xAB0DEC.. / 0xAB0E9C  法语 / 匈牙利语            —— 不碰
 *
 * 所以只改英文段的指针，让它指向我们自备的 GBK 字符串缓冲区：
 *   不碰文件 -> 不触发 DRM
 *   不碰字符串内容、不改字符串长度 -> 无余量限制
 *   指针大小不变 -> 各语言分支互不影响
 *
 * 三重自保，宁可不改也不能写坏：
 *   1. 表项地址先读回，只有恰好等于期望的英文串 VA 才改
 *   2. 目标串再逐字节比对（strcmp），任一不符即跳过该条
 *   3. 全部指针一次性 VirtualProtect→ 改 → 还原保护属性
 * Steam 更新或换了版本时 1/2 会自然失败，补丁退化为无操作。
 *
 * 编码（实测得出，曾走错一次）：UI 文本管线吃 **UTF-8**，不是系统 ANSI。
 * 依据：exe 自己的多语言串里，俄语 «Вернуть» «Качество» «Использовать»
 * «Улучшенная» 等全部是合法 UTF-8，按 CP1252 / CP1254 / GBK 解均为乱码；
 * DAT 内的中文文本同样是 UTF-8（解出「正在保存游戏」）。
 * 我曾据「这是ANSI 程序、存档路径出问题」推断 UI 也走系统 ANSI，注入 GBK，
 * 结果菜单全是问号 —— 问号正是严格 UTF-8 解码器把每个非法字节替换成
 * '?' 的表现，反过来印证了这条。故字面量必须存 UTF-8。
 * 同时不再按 GetACP() 设门槛：编码与系统代码页无关，原来的 ACP==936
 * 判断既无依据又会拦掉本该生效的环境。
 *
 * 按键名不汉化：按键名不在指针表里（表内无 Left/Space/Num.3 等），
 * 所以「设置菜单标签汉化、按键保持英文」是结构上成立的。
 */
static int patch_ui_labels(void) {
    HMODULE base;
    unsigned char *p;
    DWORD old;
    unsigned int i, done = 0;

    base = (HMODULE)GetModuleHandleW(NULL);
    if (!base) return 0;

    /* 先把整张表（含未涉及的段）设为可写一次，改完再统一还原，
     * 避免每条补丁都来回切一次保护属性。
     * 注意范围用生成器实测的常量，不用手写偏移 —— 手写过一次，
     * 把 RVA 误算成「文件偏移 - ImageBase」，整体偏了 0x400000。 */
    p = (unsigned char *)base + UI_TABLE_RVA_LO;
    if (!VirtualProtect(p, UI_TABLE_RVA_HI - UI_TABLE_RVA_LO, PAGE_READWRITE, &old))
        return 0;

    for (i = 0; i < UI_PATCH_COUNT; i++) {
        unsigned long *slot = (unsigned long *)((unsigned char *)base + ui_patches[i].rva);
        const char *cur = (const char *)(*slot);
        if (*slot != ui_patches[i].sva) continue;   /* 地址对不上，版本变了 */
        if (lstrcmpA(cur, ui_patches[i].en) != 0) continue;  /* 串内容对不上 */
        *slot = (unsigned long)(unsigned long)ui_patches[i].zh;
        done++;
    }

    VirtualProtect(p, UI_TABLE_RVA_HI - UI_TABLE_RVA_LO, old, &old);
    return (int)done;
}

/* 惰性绑定：第一次有人调用导出时才会走这里。
 * 用 InterlockedCompareExchange 保证并发首次调用只初始化一次，
 * 不会出现「指针还没写完就被另一个线程拿去调用」的半初始化竞态。
 * 注意绝不能放到 DllMain 里 —— loader lock 期间 LoadLibrary 会死锁。 */
static void bind_real(void) {
    LONG st = InterlockedCompareExchange(&g_state, 1, 0);
    if (st != 0) {                  /* 别的线程已在初始化，或已初始化完毕 */
        while (InterlockedCompareExchange(&g_state, 1, 1) != 1) Sleep(0);
        if (g_real == NULL) fatal("bind_real: init failed");
        return;
    }

    /* 见 load_system_d3d9()：必须显式找 32 位版本 */
    g_real = load_system_d3d9();
    if (!g_real) { SetLastError(ERROR_MOD_NOT_FOUND); g_state = 2; fatal("LoadLibraryW 32-bit d3d9.dll"); return; }

HMODULE g = NULL;   /* 仅占位，实际取地址一律用 g_real */

    #define GP(n) (pfn0_t)GetProcAddress(g_real, n)
    #define GP1(n) (pfn1_t)GetProcAddress(g_real, n)
    #define GP2(n) (pfn2_t)GetProcAddress(g_real, n)
    #define GP3(n) (pfn3_t)GetProcAddress(g_real, n)
    #define GP4(n) (pfn4_t)GetProcAddress(g_real, n)

    F_D3DPERF_BeginEvent                 = GP2("D3DPERF_BeginEvent");
    F_D3DPERF_EndEvent                   = GP ("D3DPERF_EndEvent");
    F_D3DPERF_GetStatus                  = GP ("D3DPERF_GetStatus");
    F_D3DPERF_QueryRepeatFrame           = GP ("D3DPERF_QueryRepeatFrame");
    F_D3DPERF_SetMarker                  = GP2("D3DPERF_SetMarker");
    F_D3DPERF_SetOptions                 = GP1("D3DPERF_SetOptions");
    F_D3DPERF_SetRegion                  = GP2("D3DPERF_SetRegion");
    F_DebugSetLevel                      = GP ("DebugSetLevel");
    F_DebugSetMute                       = GP ("DebugSetMute");
    F_Direct3D9EnableMaximizedWindowedModeShim = GP1("Direct3D9EnableMaximizedWindowedModeShim");
    F_Direct3DCreate9                    = GP1("Direct3DCreate9");
    F_Direct3DCreate9Ex                  = GP2("Direct3DCreate9Ex");
    F_Direct3DCreate9On12                = GP3("Direct3DCreate9On12");
    F_Direct3DCreate9On12Ex              = GP4("Direct3DCreate9On12Ex");
    F_PSGPError                          = GP ("PSGPError");
    F_PSGPSampleTexture                  = GP ("PSGPSampleTexture");
    (void)g;
    #undef GP
    #undef GP1
    #undef GP2
    #undef GP3
    #undef GP4

    /* 少一个都不能将就 —— 少绑一个就等于游戏调用时跳 NULL */
    if (!F_D3DPERF_BeginEvent || !F_D3DPERF_EndEvent || !F_D3DPERF_GetStatus ||
        !F_D3DPERF_QueryRepeatFrame || !F_D3DPERF_SetMarker || !F_D3DPERF_SetOptions ||
        !F_D3DPERF_SetRegion || !F_DebugSetLevel || !F_DebugSetMute ||
        !F_Direct3D9EnableMaximizedWindowedModeShim || !F_Direct3DCreate9 ||
        !F_Direct3DCreate9Ex || !F_Direct3DCreate9On12 || !F_Direct3DCreate9On12Ex ||
        !F_PSGPError || !F_PSGPSampleTexture) {
        g_state = 2; fatal("GetProcAddress missing exports");
    }

    /* 关于导出数量：本 DLL 导出 16 个，而游戏实际只会GetProcAddress
     * 一个Direct3DCreate9（实测 exe 里 LoadLibraryA("d3d9.dll") 与
     * "Direct3DCreate9" 两个字符串相邻，属运行时动态加载，
     * 导入表里根本没有 d3d9.dll 条目）。
     * 之所以仍导出全套16 个：旧版转发方案同样是这 17 个，
     * 多导出不加载没人查的符号零成本（只是导出表大一圈），
     * 而少导出会让"万一某个环境真的去查了"变成硬失败。
     * 少的那1 个是 Direct3D9ShaderValidatorCreate9 ——
     * 这个名字不存在于任何 d3d9.dll 里（SysWOW64 的 17 个具名导出中
     * 没有它），是早期版本凭想象写进 .def 的虚构导出，已删除。 */

    /* 设置菜单标签汉化。放在 bind_real 末尾而不是 DllMain：
     * DllMain 跑在 loader lock 下，那时 exe 的 .data 可能还没映射完，
     * 且 GetModuleHandle(NULL) 在极早期调用也不可靠；
     * 而每个导出桩进来都会先走 bind_real()，时序刚好。 */
    patch_ui_labels();
}

/* ---- 17 个导出桩。参数个数来自实测，见上表 ----
 * 注意：这里【不能】加 __declspec(dllexport)。导出名由 d3d9.def 做别名映射
 * （Direct3DCreate9 = stub_Direct3DCreate9），而 gcc 会把 x86 stdcall 桩函数
 * 修饰成 _stub_Direct3DCreate9@4 这样的名字。
 * 若同时加 dllexport，dll 会同时导出 stub_* 和映射后的 17 个名字，
 * 变成 34 个导出 —— 游戏只按后者导入，多出来的 17 个纯属噪音，
 * 还会让 check_exports.py 的「多余导出」检查误报。
 * 同理 gcc 的 --kill-at 只负责去掉符号名的 @N 后缀，别名映射仍由 .def 负责。 */
/* 绑不上时返回 0/NULL 而不是崩 —— 对游戏而言"这个可选功能不可用"
 * 比"跳到空指针"友好得多，且这些函数本身都不在正常渲染路径上。 */
#define STUB0(name)  long WINAPI stub_##name(void)   { bind_real(); return F_##name ? F_##name() : 0; }
#define STUB1(name)  long WINAPI stub_##name(DWORD a) { bind_real(); return F_##name(a); }
#define STUB2(name)  long WINAPI stub_##name(DWORD a, DWORD b) { bind_real(); return F_##name(a, b); }
#define STUB3(name)  long WINAPI stub_##name(DWORD a, DWORD b, DWORD c) { bind_real(); return F_##name(a, b, c); }
#define STUB4(name)  long WINAPI stub_##name(DWORD a, DWORD b, DWORD c, DWORD d) { bind_real(); return F_##name(a, b, c, d); }

STUB2(D3DPERF_BeginEvent)
STUB0(D3DPERF_EndEvent)
STUB0(D3DPERF_GetStatus)
STUB0(D3DPERF_QueryRepeatFrame)
STUB2(D3DPERF_SetMarker)
STUB1(D3DPERF_SetOptions)
STUB2(D3DPERF_SetRegion)
STUB0(DebugSetLevel)
STUB0(DebugSetMute)
STUB1(Direct3D9EnableMaximizedWindowedModeShim)
STUB1(Direct3DCreate9)
STUB2(Direct3DCreate9Ex)
STUB3(Direct3DCreate9On12)
STUB4(Direct3DCreate9On12Ex)
STUB0(PSGPError)
STUB0(PSGPSampleTexture)

#undef STUB0
#undef STUB1
#undef STUB2
#undef STUB3
#undef STUB4

/* ANSI -> Unicode（CP1254），失败返回 NULL（调用者回退原函数）。
 * 长度上限 32768：MAX_PATH 路径远小于此，超过就说明上游给了非路径数据
 * 或有 bug，直接放弃转换比分配巨块内存安全。 */
#define PATH_LIMIT 32768

static WCHAR* to_wide(LPCSTR s) {
    if (!s) return NULL;
    int n = MultiByteToWideChar(1254, 0, s, -1, NULL, 0);
    if (n <= 0 || n > PATH_LIMIT) return NULL;
    WCHAR* w = (WCHAR*)malloc((size_t)n * sizeof(WCHAR));
    if (!w) return NULL;
    if (MultiByteToWideChar(1254, 0, s, -1, w, n) <= 0) { free(w); return NULL; }
    return w;
}

/* ------------------------------------------------------------------ hook 函数 */
static HANDLE WINAPI HookCreateFileA(LPCSTR n, DWORD a, DWORD b, LPSECURITY_ATTRIBUTES c, DWORD d, DWORD e, HANDLE f) {
    WCHAR* w = to_wide(n);
    if (w) {
        HANDLE r = CreateFileW(w, a, b, c, d, e, f);
        free(w);
        return r;
    }
    return RealCreateFileA(n, a, b, c, d, e, f);
}

static BOOL WINAPI HookCreateDirectoryA(LPCSTR n, LPSECURITY_ATTRIBUTES a) {
    WCHAR* w = to_wide(n);
    if (w) { BOOL r = CreateDirectoryW(w, a); free(w); return r; }
    return RealCreateDirectoryA(n, a);
}

static BOOL WINAPI HookDeleteFileA(LPCSTR n) {
    WCHAR* w = to_wide(n);
    if (w) { BOOL r = DeleteFileW(w); free(w); return r; }
    return RealDeleteFileA(n);
}

static BOOL WINAPI HookRemoveDirectoryA(LPCSTR n) {
    WCHAR* w = to_wide(n);
    if (w) { BOOL r = RemoveDirectoryW(w); free(w); return r; }
    return RealRemoveDirectoryA(n);
}

static DWORD WINAPI HookGetFileAttributesA(LPCSTR n) {
    WCHAR* w = to_wide(n);
    if (w) { DWORD r = GetFileAttributesW(w); free(w); return r; }
    return RealGetFileAttributesA(n);
}

static BOOL WINAPI HookSetFileAttributesA(LPCSTR n, DWORD a) {
    WCHAR* w = to_wide(n);
    if (w) { BOOL r = SetFileAttributesW(w, a); free(w); return r; }
    return RealSetFileAttributesA(n, a);
}

static BOOL WINAPI HookMoveFileA(LPCSTR a, LPCSTR b) {
    WCHAR* wa = to_wide(a);
    WCHAR* wb = to_wide(b);
    if (wa && wb) { BOOL r = MoveFileW(wa, wb); free(wa); free(wb); return r; }
    if (wa) free(wa); if (wb) free(wb);
    return RealMoveFileA(a, b);
}

static BOOL WINAPI HookCopyFileA(LPCSTR a, LPCSTR b, BOOL f) {
    WCHAR* wa = to_wide(a);
    WCHAR* wb = to_wide(b);
    if (wa && wb) { BOOL r = CopyFileW(wa, wb, f); free(wa); free(wb); return r; }
    if (wa) free(wa); if (wb) free(wb);
    return RealCopyFileA(a, b, f);
}

static HANDLE WINAPI HookFindFirstFileA(LPCSTR n, LPWIN32_FIND_DATAA fd) {
    WCHAR* w = to_wide(n);
    if (w && fd) {
        WIN32_FIND_DATAW fdw;
        HANDLE h = FindFirstFileW(w, &fdw);
        free(w);
        if (h != INVALID_HANDLE_VALUE) {
            memset(fd, 0, sizeof(*fd));
            fd->dwFileAttributes = fdw.dwFileAttributes;
            fd->ftCreationTime = fdw.ftCreationTime;
            fd->ftLastAccessTime = fdw.ftLastAccessTime;
            fd->ftLastWriteTime = fdw.ftLastWriteTime;
            fd->nFileSizeHigh = fdw.nFileSizeHigh;
            fd->nFileSizeLow = fdw.nFileSizeLow;
            WideCharToMultiByte(1254, 0, fdw.cFileName, -1, fd->cFileName, MAX_PATH, NULL, NULL);
            /* 14 = sizeof(fd->cAlternateFileName)（WIN32_FIND_DATAA 里 8.3 短名固定 13 字节 + NUL）。
             * 写死数字会随 SDK 布局变化而越界，改成编译期求值。 */
            WideCharToMultiByte(1254, 0, fdw.cAlternateFileName, -1,
                                fd->cAlternateFileName, (int)sizeof(fd->cAlternateFileName), NULL, NULL);
        }
        return h;
    }
    if (w) free(w);
    return RealFindFirstFileA(n, fd);
}

static BOOL WINAPI HookFindNextFileA(HANDLE h, LPWIN32_FIND_DATAA fd) {
    if (fd) {
        WIN32_FIND_DATAW fdw;
        BOOL r = FindNextFileW(h, &fdw);
        if (r) {
            memset(fd, 0, sizeof(*fd));
            fd->dwFileAttributes = fdw.dwFileAttributes;
            fd->ftCreationTime = fdw.ftCreationTime;
            fd->ftLastAccessTime = fdw.ftLastAccessTime;
            fd->ftLastWriteTime = fdw.ftLastWriteTime;
            fd->nFileSizeHigh = fdw.nFileSizeHigh;
            fd->nFileSizeLow = fdw.nFileSizeLow;
            WideCharToMultiByte(1254, 0, fdw.cFileName, -1, fd->cFileName, MAX_PATH, NULL, NULL);
            /* 14 = sizeof(fd->cAlternateFileName)（WIN32_FIND_DATAA 里 8.3 短名固定 13 字节 + NUL）。
             * 写死数字会随 SDK 布局变化而越界，改成编译期求值。 */
            WideCharToMultiByte(1254, 0, fdw.cAlternateFileName, -1,
                                fd->cAlternateFileName, (int)sizeof(fd->cAlternateFileName), NULL, NULL);
        }
        return r;
    }
    return RealFindNextFileA(h, fd);
}

/* ------------------------------------------------------------------ IAT hook */
static void* FindIATEntry(const char* dllName, const char* funcName) {
    HMODULE base = GetModuleHandleW(NULL);
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)base;
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((BYTE*)base + dos->e_lfanew);
    IMAGE_DATA_DIRECTORY imp = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    PIMAGE_IMPORT_DESCRIPTOR desc = (PIMAGE_IMPORT_DESCRIPTOR)((BYTE*)base + imp.VirtualAddress);
    for (; desc->Name; desc++) {
        const char* name = (const char*)((BYTE*)base + desc->Name);
        if (_stricmp(name, dllName) == 0) {
            PIMAGE_THUNK_DATA thunk = (PIMAGE_THUNK_DATA)((BYTE*)base + desc->FirstThunk);
            PIMAGE_THUNK_DATA orig = (PIMAGE_THUNK_DATA)((BYTE*)base + (desc->OriginalFirstThunk ? desc->OriginalFirstThunk : desc->FirstThunk));
            for (; orig->u1.AddressOfData; orig++, thunk++) {
                if (orig->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
                PIMAGE_IMPORT_BY_NAME ibn = (PIMAGE_IMPORT_BY_NAME)((BYTE*)base + orig->u1.AddressOfData);
                if (strcmp((char*)ibn->Name, funcName) == 0)
                    return &thunk->u1.Function;
            }
        }
    }
    return NULL;
}

static void PatchIAT(const char* dll, const char* func, void* newfn) {
    void* entry = FindIATEntry(dll, func);
    if (entry) {
        DWORD old;
        VirtualProtect(entry, sizeof(void*), PAGE_READWRITE, &old);
        *(void**)entry = newfn;
        VirtualProtect(entry, sizeof(void*), old, &old);
    }
}

/* ==================================================================== 内存字符串补丁 —— 已停用
 *
 * 停用原因（原「一并修掉」里指出的乱码）：这里把中文以 **UTF-8 字节**写进 exe，
 * 但游戏渲染 UI 用的是 CP1252/1254 字体解码路径，UTF-8 中文会被逐字节拆成
 * 若干个西欧字符显示，也就是所谓的乱码 —— 自己看着是补丁，别人机器上是乱码。
 * 真要汉化 UI，得生成 GBK/CP936 字节（中文 Windows 原生代码页）而不是 UTF-8，
 * 且每个槽位长度必须重新核算。当前汉化已由 GAME2.dat 的 text.csv 完整覆盖，
 * 所以这里整块停用，不再动 exe 数据段。
 *
 * 保留代码是为了留个记录：万一以后要走这条路，槽位表和教训都在这儿。
 * 需要时把 #if 0 改成 #if 1，并先把 str_patches[].zh 的编码方式改对。
 */
#if 0
typedef struct { DWORD rva; const char* zh; int clr; } str_patch_t;
static const str_patch_t str_patches[] = {
    /* ---- 视频/特效设置页 标题+值+通用按钮（0x895xxx 区，二分定位：单独验证安全性） ---- */
    {0x895708, "纹理质量", 16},
    {0x895718, "使用当前设置", 24},
    {0x895730, "跟随屏幕", 16},
    {0x895740, "增强图形", 20},
    {0x895754, "宽高比", 16},
    {0x895764, "垂直同步", 16},
    {0x895774, "刷新率", 16},
    {0x895784, "屏幕分辨率", 20},
    {0x895798, "视频设置", 16},
    {0x8957a8, "恢复默认设置", 20},
    {0x8957bc, "取消", 8},
    {0x8957c4, "好", 4},
    {0x8957c8, "否", 4},
    {0x8957cc, "是", 4},
    {0x8957d0, "拒绝", 8},
    {0x8957d8, "接受", 8},
    {0x8957e0, "继续", 8},
    {0x8957e8, "中", 8},
    {0x8957f0, "返回游戏", 16},
    {0x895800, "退出演示菜单", 20},
    {0x895814, "返回桌面", 16},
    {0x895824, "退出", 8},
    {0x8955b0, "接受", 12},
    {0x89562c, "显示游戏控制", 20},
    {0x895640, "环境光遮蔽", 20},
    {0x89565c, "动态光质量", 24},
    {0x895674, "模糊", 12},
    {0x895680, "景深", 16},
    {0x895690, "泛光", 8},
    {0x895698, "阴影", 8},
    {0x8956a0, "外部设置", 16},
    {0x8956b0, "特效设置", 20},
    {0x8956c4, "你必须重启游戏才能让这些更改生效！", 60},
    /* ---- 布尔选项值 On/Off（0x876 区，引擎所有开关选项共用的值表） ---- */
    {0x8763e0, "关", 4},
    {0x8763e4, "开", 4},
    /* ---- 剩余选项值（Widescreen 在 0x895 安全区；其余待验证） ---- */
    {0x895a60, "宽屏", 12},
    {0x908b5c, "无阴影", 12},
    {0x89a984, "高", 8},
    {0x89a98c, "低", 4},
    /* 0x878dca(Shadows) 在 0x878 区，暂不补 */
    /* ---- 键位名称：已确认导致 logo 飘移，禁用 ---- */
    /* {0x896734, "数0", 8}, */
    /* {0x896800, "数1", 8}, */
    /* {0x8967bc, "数2", 8}, */
    /* {0x896778, "数3", 8}, */
    /* {0x896910, "数4", 8}, */
    /* {0x8968cc, "数5", 8}, */
    /* {0x896888, "数6", 8}, */
    /* {0x896a20, "数7", 8}, */
    /* {0x8969dc, "数8", 8}, */
    /* {0x896998, "数9", 8}, */
    /* {0x89668c, "数回车", 12}, */
    /* {0x896844, "数+", 8}, */
    /* {0x896954, "数-", 8}, */
    /* {0x896bd8, "数*", 8}, */
    /* {0x8965c8, "数/", 8}, */
    /* {0x896430, "左", 8}, */
    /* {0x8963d0, "右", 8}, */
    /* 上/下 键名匹配到的是文本输入的 'Up'/'Down'，非键位表，移除以免写坏数据 */
    /* {0x888b9c, "上", 4}, */
    /* {0x888b94, "下", 8}, */
    /* {0x896b48, "空格", 8}, */
    /* {0x896d30, "回车", 8}, */
    /* {0x896620, "右Ctrl", 8}, */
    /* {0x896d08, "左Ctrl", 8}, */
    /* {0x896c48, "右Shift", 12}, */
    /* {0x896cb0, "左Shift", 12}, */
    /* {0x896540, "右Alt", 8}, */
    /* {0x8960b8, "左Alt", 8}, */
    /* {0x8962bc, "插入", 8}, */
    /* {0x896440, "上页", 8}, */
    /* {0x896438, "上页", 8}, */
    /* {0x8962cc, "下页", 12}, */
    /* {0x8962c4, "下页", 8}, */
    /* {0x89615c, "退格", 12}, */
    /* ---- 按键设置提示（0x89a/0x878 区，禁用） ---- */
    /* {0x89a6d8, "你必须配置所有按键", 32}, */
    /* {0x89a6f8, "你必须配置这些按键", 32}, */
    /* {0x89a718, "按键不足", 20}, */
    /* {0x89a748, "无输入", 12}, */
    /* {0x878304, "无信息", 26}, */
    /* {0x878e60, "按B打开选项", 26}, */
};

static void patch_strings(void) {
    HMODULE base = GetModuleHandleW(NULL);
    if (!base) return;
    size_t i;
    for (i = 0; i < sizeof(str_patches) / sizeof(str_patches[0]); i++) {
        char* p = (char*)base + str_patches[i].rva;
        size_t zl = strlen(str_patches[i].zh);
        DWORD old;
        if (zl + 1 > (size_t)str_patches[i].clr) continue;  /* 超长则跳过 */
        VirtualProtect(p, str_patches[i].clr, PAGE_READWRITE, &old);
        memset(p, 0, str_patches[i].clr);
        memcpy(p, str_patches[i].zh, zl);
        p[zl] = 0;
        VirtualProtect(p, str_patches[i].clr, old, &old);
    }
}
#endif /* 0：字符串补丁已停用 */

/* ------------------------------------------------------------------ DllMain */
static void patch_all_iat(void) {
    PatchIAT("kernel32.dll", "CreateFileA", (void*)HookCreateFileA);
    PatchIAT("kernel32.dll", "CreateDirectoryA", (void*)HookCreateDirectoryA);
    PatchIAT("kernel32.dll", "DeleteFileA", (void*)HookDeleteFileA);
    PatchIAT("kernel32.dll", "RemoveDirectoryA", (void*)HookRemoveDirectoryA);
    PatchIAT("kernel32.dll", "GetFileAttributesA", (void*)HookGetFileAttributesA);
    PatchIAT("kernel32.dll", "SetFileAttributesA", (void*)HookSetFileAttributesA);
    PatchIAT("kernel32.dll", "MoveFileA", (void*)HookMoveFileA);
    PatchIAT("kernel32.dll", "FindFirstFileA", (void*)HookFindFirstFileA);
    PatchIAT("kernel32.dll", "FindNextFileA", (void*)HookFindNextFileA);
    PatchIAT("kernel32.dll", "CopyFileA", (void*)HookCopyFileA);
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        HMODULE k = GetModuleHandleA("kernel32.dll");
        RealCreateFileA = (CreateFileA_t)GetProcAddress(k, "CreateFileA");
        RealCreateDirectoryA = (CreateDirectoryA_t)GetProcAddress(k, "CreateDirectoryA");
        RealDeleteFileA = (DeleteFileA_t)GetProcAddress(k, "DeleteFileA");
        RealRemoveDirectoryA = (RemoveDirectoryA_t)GetProcAddress(k, "RemoveDirectoryA");
        RealGetFileAttributesA = (GetFileAttributesA_t)GetProcAddress(k, "GetFileAttributesA");
        RealSetFileAttributesA = (SetFileAttributesA_t)GetProcAddress(k, "SetFileAttributesA");
        RealMoveFileA = (MoveFileA_t)GetProcAddress(k, "MoveFileA");
        RealFindFirstFileA = (FindFirstFileA_t)GetProcAddress(k, "FindFirstFileA");
        RealFindNextFileA = (FindNextFileA_t)GetProcAddress(k, "FindNextFileA");
        RealCopyFileA = (CopyFileA_t)GetProcAddress(k, "CopyFileA");

        patch_all_iat();

        /* 这里刻意【不】调用 bind_real()：
         * DllMain 跑在 loader lock 下，期间 LoadLibrary 会与加载器互相等待 → 死锁。
         * 真正的系统 d3d9 加载推迟到第一次有导出被调用时（见 bind_real 的注释）。 */
    }
    return TRUE;
}
