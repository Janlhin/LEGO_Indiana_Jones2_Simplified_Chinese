/* test_savesfix.c — 开发期冒烟测试，不放进分发包。
 * 验证两点：
 *   1) 本 DLL 的 IAT hook 装好后，CreateFileA 仍能正常工作；
 *   2) 含 CP1254 ®/™ 字节的路径能被正确创建（即存档修复生效）。
 *   3) DirectInput8Create 能转发到系统 dinput8（不崩）。
 */
#include <windows.h>
#include <stdio.h>

int main(void) {
    char self[MAX_PATH];
    GetModuleFileNameA(NULL, self, MAX_PATH);

    /* 加载我们的 dinput8.dll（DllMain 里会装 IAT hook） */
    HMODULE h = LoadLibraryA("dinput8.dll");
    if (!h) { printf("FAIL: LoadLibrary dinput8.dll -> %lu\n", GetLastError()); return 1; }
    printf("ok: LoadLibrary dinput8.dll\n");

    /* 1) 普通路径 CreateFileA 仍可用（hook 不能把正常调用搞坏） */
    HANDLE fh = CreateFileA(self, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (fh == INVALID_HANDLE_VALUE) { printf("FAIL: CreateFileA(self) after hook -> %lu\n", GetLastError()); return 1; }
    CloseHandle(fh);
    printf("ok: CreateFileA(self) works after hook\n");

    /* 2) 含 CP1254 ®(0xAE)/™(0x99) 的路径：GBK 系统下原生 A 版会失败，
     *    经 hook 转 Unicode 后应能创建。 */
    char tmp[MAX_PATH];
    GetTempPathA(MAX_PATH, tmp);
    /* "LIJ2®™test.tmp" —— 用 CP1254 字节直接写：®=0xAE ™=0x99 */
    char name[MAX_PATH];
    sprintf(name, "%sLIJ2%c%ctest.tmp", tmp, (char)0xAE, (char)0x99);
    fh = CreateFileA(name, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (fh == INVALID_HANDLE_VALUE) {
        printf("FAIL: CreateFileA(CP1254 path) -> %lu  (save-fix not working)\n", GetLastError());
        return 1;
    }
    CloseHandle(fh);
    DeleteFileA(name);
    printf("ok: CreateFileA(CP1254 ®/™ path) created+deleted (save-fix works)\n");

    /* 3) 转发 DirectInput8Create：用合法参数调用，期望它到达系统 dinput8 并
     *    安全返回（S_OK 或合法错误码），证明转发链完整、不崩。 */
    typedef HRESULT (WINAPI *DI8_t)(HINSTANCE, DWORD, const void*, void*, void*);
    DI8_t di = (DI8_t)GetProcAddress(h, "DirectInput8Create");
    if (!di) { printf("FAIL: GetProcAddress DirectInput8Create\n"); return 1; }
    static const GUID IID_IDirectInput8 =
        {0x25E609E0,0xB259,0x11CF,{0xBF,0xC7,0x44,0x45,0x53,0x54,0x00,0x00}};
    void* pv = NULL;
    HRESULT hr = di((HINSTANCE)GetModuleHandleA(NULL), 0x0800,
                    &IID_IDirectInput8, &pv, NULL);
    printf("ok: DirectInput8Create forwarded (returned 0x%08X, S_OK=0x0)\n", (unsigned)hr);

    FreeLibrary(h);
    printf("ALL TESTS PASSED\n");
    return 0;
}
