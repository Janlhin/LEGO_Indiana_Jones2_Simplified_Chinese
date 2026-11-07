/* savesfix.c — 独立「存档修复」DLL（不依赖 / 不覆盖中文补丁）
 *
 * 背景（细节见仓库 README「存档修复」一节）：
 *   LEGO Indiana Jones 2 是 2009 年的非 Unicode 程序，只用 ANSI 文件 API
 *   （CreateFileA / CreateDirectoryA / FindFirstFileA …），且 exe 硬编码了
 *   CP1252/1254 编码的存档目录名 "LEGO® Indiana Jones™ 2"（®=0xAE, ™=0x99）。
 *   中文系统（GBK/CP936）下这些字节被内核转成 '?'（非法文件名）→ 存档失败跳出。
 *
 *   本 DLL 通过 IAT hook 拦截这 10 个 A 版 API，把路径按 CP1254 转成 Unicode
 *   后调 W 版，从而绕过内核的 GBK 转换。纯 ASCII 路径在 CP1254 下映射不变，
 *   对其它路径无副作用。
 *
 *   这套修复逻辑原本内嵌在中文补丁的 d3d9.dll（d3d9proxy）里。本文件把它抽成
 *   **一个独立的 DLL**，靠文件名劫持 DINPUT8.DLL 这一**与 d3d9 不冲突**的槽位被
 *   加载。由此带来的好处：
 *     - 永远不会覆盖 / 占用中文补丁的 d3d9.dll 槽位（即「无中文补丁覆盖」）；
 *     - 可单独使用 —— 只想修存档、不要汉化时，只放本 DLL 即可；
 *     - 与中文补丁的 d3d9.dll 并存时，两处 IAT patch 都指向真实 kernel32，互不影响。
 *
 *   导出策略（关键）：游戏静态导入 DINPUT8.DLL 的 DirectInput8Create（仅 1 个）。
 *   本 DLL 运行时自行定位 32 位系统 dinput8.dll 并转发，不附带任何系统 DLL 副本
 *   （避免 d3d9_orig.dll 那种版本被钉死的老问题）。其余逻辑只是纯粹的 IAT hook。
 */

#include <windows.h>
#include <stdlib.h>
#include <string.h>

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

/* PATH_LIMIT：MAX_PATH 远小于此；超过说明上游给了非路径数据或有 bug，放弃转换。 */
#define PATH_LIMIT 32768

/* ANSI(CP1254) -> Unicode。失败返回 NULL（调用者回退原函数）。 */
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
            WideCharToMultiByte(1254, 0, fdw.cAlternateFileName, -1,
                                fd->cAlternateFileName, (int)sizeof(fd->cAlternateFileName), NULL, NULL);
        }
        return r;
    }
    return RealFindNextFileA(h, fd);
}

/* ------------------------------------------------------------------ IAT hook */
static void* FindIATEntry(const char* dllName, const char* funcName) {
    HMODULE base = GetModuleHandleW(NULL);   /* 游戏 exe 自身 */
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

/* ==================================================================== 转发系统 dinput8.dll
 *
 * 游戏静态导入 DINPUT8.DLL 的 DirectInput8Create（仅 1 个导出）。
 * 本 DLL 必须把这个调用转发到真正的系统 dinput8.dll，否则游戏初始化输入即失败。
 *
 * 定位系统 32 位 dinput8.dll 的逻辑，沿用 d3d9proxy 在 Win11 24H2 + 32 位进程上
 * 实测验证过的结论：GetSystemDirectoryW 对 32 位进程返回的是 system32（内含 64 位
 * 副本），需按 IsWow64Process 把 system32 换成 SysWOW64 才能拿到 32 位那份。
 */
typedef long (WINAPI *pfn5_t)(DWORD, DWORD, DWORD, DWORD, DWORD);

static pfn5_t F_DirectInput8Create;
static HMODULE g_real;                 /* 系统 dinput8.dll 句柄 */
static volatile LONG g_state;          /* 0=未初始化 1=初始化中 2=失败 3=成功 */

static HMODULE load_system_dll(const WCHAR* name) {
    WCHAR dir[MAX_PATH];
    UINT n = GetSystemDirectoryW(dir, MAX_PATH);
    if (n == 0 || n >= MAX_PATH - 16) { SetLastError(ERROR_INSUFFICIENT_BUFFER); return NULL; }

    typedef BOOL (WINAPI *IsWow64Process_t)(HANDLE, PBOOL);
    IsWow64Process_t pIsWow64 =
        (IsWow64Process_t)GetProcAddress(GetModuleHandleA("kernel32.dll"), "IsWow64Process");
    if (!pIsWow64) { SetLastError(ERROR_PROC_NOT_FOUND); return NULL; }

    BOOL wow64 = FALSE;
    if (!pIsWow64(GetCurrentProcess(), &wow64)) return NULL;

    if (wow64) {
        WCHAR* tail = NULL;
        UINT i;
        for (i = n; i > 0; i--) {
            if (dir[i - 1] == L'\\') { tail = dir + i - 1; break; }
        }
        if (!tail) { SetLastError(ERROR_PATH_NOT_FOUND); return NULL; }

        size_t prefix = (size_t)(tail - dir) + 1;   /* 含末尾的 '\' */
        static const WCHAR kWow[] = L"SysWOW64";
        const size_t kWowLen = 8;
        if (prefix + kWowLen + 16 >= MAX_PATH) {     /* +16 留给 "\<name>" 与 NUL */
            SetLastError(ERROR_INSUFFICIENT_BUFFER);
            return NULL;
        }
        dir[prefix] = 0;
        memcpy(dir + prefix, kWow, kWowLen * sizeof(WCHAR));
        dir[prefix + kWowLen] = 0;
        n = (UINT)(prefix + kWowLen);
    }

    if (n + 1 + (UINT)wcslen(name) >= MAX_PATH) { SetLastError(ERROR_INSUFFICIENT_BUFFER); return NULL; }
    lstrcatW(dir, L"\\");
    lstrcatW(dir, name);
    return LoadLibraryW(dir);
}

/* 惰性绑定：第一次有人调用 DirectInput8Create 时才走这里。
 * 绝不放进 DllMain —— loader lock 期间 LoadLibrary 会死锁。 */
static void bind_real(void) {
    LONG st = InterlockedCompareExchange(&g_state, 1, 0);
    if (st != 0) {                  /* 别的线程已在初始化，或已初始化完毕 */
        while (InterlockedCompareExchange(&g_state, 1, 1) != 1) Sleep(0);
        return;
    }

    g_real = load_system_dll(L"dinput8.dll");
    if (!g_real) { g_state = 2; return; }

    F_DirectInput8Create = (pfn5_t)GetProcAddress(g_real, "DirectInput8Create");
    if (!F_DirectInput8Create) { g_state = 2; return; }

    g_state = 3;
}

/* 转发桩。绑不上时返回 0（游戏会把它当作 DirectInput 初始化失败来处理，
 * 属于环境层面的严重问题；存档修复的 IAT hook 与此无关，已在 DllMain 里独立装好）。 */
long WINAPI stub_DirectInput8Create(DWORD a, DWORD b, DWORD c, DWORD d, DWORD e) {
    if (g_state != 3) bind_real();
    return F_DirectInput8Create ? F_DirectInput8Create(a, b, c, d, e) : 0;
}

/* ------------------------------------------------------------------ DllMain */
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

        /* 装好存档修复的 IAT hook。这里只用 GetProcAddress + VirtualProtect，
         * 不调 LoadLibrary，loader lock 下安全（与 d3d9proxy 同款做法）。 */
        patch_all_iat();
    }
    return TRUE;
}
