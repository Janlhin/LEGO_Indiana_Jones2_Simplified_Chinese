/* 本文件由 tools/gen_ui_patch.py 自动生成，请勿手改。
 * 源 exe: D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2\LEGOIndy2.exe
 * 指针表: .data 原始偏移 0xAB09F0..0xAB17E4
 *   cvar 名段   0xAB0B48 之前（pcconfig.txt 键名，不汉化）
 *   英文段 10xAB0B5C..0xAB0C9C（40 项）
 *   英文段 20xAB0CA4..0xAB0DE4（40 项）
 * 映像基址 0x00400000
 *
 * 注意中文常量存的是 **UTF-8** 字节 —— 实测 exe 的 UI 文本管线
 * 吃 UTF-8（俄语/法语等语言串全为合法 UTF-8）。写 GBK 会全屏问号，
 * 因为严格 UTF-8 解码器会把非法字节逐个替换成 '?'。
 */
#ifndef UI_PATCH_H
#define UI_PATCH_H

/* 40 个标签的 UTF-8 字节串（供补丁做运行时比对，也可单独用于自检） */
static const char *const ui_zh_label[] = {
    "\xe9\x80\x80\xe5\x87\xba",   /* Quit */
    "\xe9\x80\x80\xe5\x87\xba\xe5\x88\xb0\x20\x57\x69\x6e\x64\x6f\x77\x73",   /* Quit to Windows */
    "\xe9\x80\x80\xe5\x87\xba\xe5\x88\xb0\xe6\xbc\x94\xe7\xa4\xba\xe8\x8f\x9c\xe5\x8d\x95",   /* Quit to Demos Menu */
    "\xe8\xbf\x94\xe5\x9b\x9e\xe6\xb8\xb8\xe6\x88\x8f",   /* Return to game */
    "\xe4\xbd\x8e",   /* Low */
    "\xe4\xb8\xad",   /* Medium */
    "\xe9\xab\x98",   /* High */
    "\xe7\xbb\xa7\xe7\xbb\xad\xe6\xb8\xb8\xe6\x88\x8f",   /* Resume */
    "\xe6\x8e\xa5\xe5\x8f\x97",   /* Accept */
    "\xe8\xbf\x94\xe5\x9b\x9e",   /* Back */
    "\xe6\x8b\x92\xe7\xbb\x9d",   /* Decline */
    "\xe6\x98\xaf",   /* Yes */
    "\xe5\x90\xa6",   /* No */
    "\xe7\xa1\xae\xe5\xae\x9a",   /* OK */
    "\xe5\x8f\x96\xe6\xb6\x88",   /* Cancel */
    "\xe5\xbc\x80",   /* On */
    "\xe5\x85\xb3",   /* Off */
    "\xe6\x81\xa2\xe5\xa4\x8d\xe9\xbb\x98\xe8\xae\xa4\xe8\xae\xbe\xe7\xbd\xae",   /* Reset To Defaults */
    "\xe7\x94\xbb\xe9\x9d\xa2\xe8\xae\xbe\xe7\xbd\xae",   /* Video Settings */
    "\xe5\xb1\x8f\xe5\xb9\x95\xe5\x88\x86\xe8\xbe\xa8\xe7\x8e\x87",   /* Screen Resolution */
    "\xe5\x88\xb7\xe6\x96\xb0\xe7\x8e\x87",   /* Refresh Rate */
    "\xe5\x9e\x82\xe7\x9b\xb4\xe5\x90\x8c\xe6\xad\xa5",   /* Vertical Sync */
    "\xe5\xae\xbd\xe9\xab\x98\xe6\xaf\x94",   /* Aspect Ratio */
    "\xe5\xa2\x9e\xe5\xbc\xba\xe7\x94\xbb\xe8\xb4\xa8",   /* Enhanced Graphics */
    "\xe8\xb7\x9f\xe9\x9a\x8f\xe5\x88\x86\xe8\xbe\xa8\xe7\x8e\x87",   /* From Screen-Res */
    "\xe4\xbd\xbf\xe7\x94\xa8\xe5\xbd\x93\xe5\x89\x8d\xe8\xae\xbe\xe7\xbd\xae",   /* Use current settings */
    "\xe7\xba\xb9\xe7\x90\x86\xe8\xb4\xa8\xe9\x87\x8f",   /* Texture Quality */
    "\xe8\xbf\x98\xe5\x8e\x9f",   /* Revert */
    "\xe9\x9c\x80\xe8\xa6\x81\xe9\x87\x8d\xe5\x90\xaf\xe6\xb8\xb8\xe6\x88\x8f\xe6\x89\x8d\xe8\x83\xbd\xe8\xae\xa9\xe8\xbf\x99\xe4\xba\x9b\xe8\xae\xbe\xe7\xbd\xae\xe7\x94\x9f\xe6\x95\x88",   /* You must restart the game for these changes to take effect! */
    "\xe7\x89\xb9\xe6\x95\x88\xe8\xae\xbe\xe7\xbd\xae",   /* Effects Settings */
    "\xe5\x85\xa8\xe5\xb1\x8f\xe6\x8a\x97\xe9\x94\xaf\xe9\xbd\xbf",   /* FSAA */
    "\xe5\xa4\x96\xe9\x83\xa8\xe8\xae\xbe\xe7\xbd\xae",   /* Externally Set */
    "\xe9\x98\xb4\xe5\xbd\xb1",   /* Shadows */
    "\xe6\xb3\x9b\xe5\x85\x89",   /* Bloom */
    "\xe6\x99\xaf\xe6\xb7\xb1",   /* Depth of Field */
    "\xe9\x80\x9f\xe5\xba\xa6\xe6\xa8\xa1\xe7\xb3\x8a",   /* Speed Blur */
    "\xe5\x8a\xa8\xe6\x80\x81\xe5\x85\x89\xe5\xbd\xb1\xe8\xb4\xa8\xe9\x87\x8f",   /* Dynamic Light Quality */
    "\xe8\xbe\xb9\xe8\xa7\x92\xe6\x8a\x97\xe9\x94\xaf\xe9\xbd\xbf",   /* Edge AA */
    "\xe7\x8e\xaf\xe5\xa2\x83\xe5\x85\x89\xe9\x81\xae\xe8\x94\xbd",   /* Ambient Occlusion */
    "\xe6\x98\xbe\xe7\xa4\xba\xe6\xb8\xb8\xe6\x88\x8f\xe6\x8c\x89\xe9\x94\xae",   /* Show Game Controls */
};
#define UI_ZH_COUNT 40

/* 每条补丁：
 *   rva   = 指针项自身在映像内的偏移（改的是这 4 个字节）
 *   sva   = 该指针当前应指向的英文串 VA（比对用）
 *   en    = 该英文串（比对用）
 *   zh    = 自备 UTF-8 串（改指向它）
 *
 * rva 的算法：指针表在 .data 节，实测该节 VA == RawAddr（见
 * tools/verify_rva_maps.py），所以文件偏移**本身就是 RVA**，
 * 不能减 ImageBase。早先写成 off-ImageBase 会整体偏 0x400000，
 * 补丁会写到完全无关的内存地址上。
 */
typedef struct {
    unsigned long rva;
    unsigned long sva;
    const char *en;
    const char *zh;
} ui_patch_t;

/* 整张指针表（含未涉及的 cvar 与其它语言段）的范围，
 * 供一次性 VirtualProtect 用。 */
#define UI_TABLE_RVA_LO 0xAB09F0UL
#define UI_TABLE_RVA_HI 0xAB17E4UL

static const ui_patch_t ui_patches[] = {
    { 0xAB0B5CUL, 0x00C95824UL, "\x51\x75\x69\x74", ui_zh_label[0] },  /* Quit */
    { 0xAB0B64UL, 0x00C95814UL, "\x51\x75\x69\x74\x20\x74\x6f\x20\x57\x69\x6e\x64\x6f\x77\x73", ui_zh_label[1] },  /* Quit to Windows */
    { 0xAB0B6CUL, 0x00C95800UL, "\x51\x75\x69\x74\x20\x74\x6f\x20\x44\x65\x6d\x6f\x73\x20\x4d\x65\x6e\x75", ui_zh_label[2] },  /* Quit to Demos Menu */
    { 0xAB0B74UL, 0x00C957F0UL, "\x52\x65\x74\x75\x72\x6e\x20\x74\x6f\x20\x67\x61\x6d\x65", ui_zh_label[3] },  /* Return to game */
    { 0xAB0B7CUL, 0x00C9A98CUL, "\x4c\x6f\x77", ui_zh_label[4] },  /* Low */
    { 0xAB0B84UL, 0x00C957E8UL, "\x4d\x65\x64\x69\x75\x6d", ui_zh_label[5] },  /* Medium */
    { 0xAB0B8CUL, 0x00C9A984UL, "\x48\x69\x67\x68", ui_zh_label[6] },  /* High */
    { 0xAB0B94UL, 0x00C957E0UL, "\x52\x65\x73\x75\x6d\x65", ui_zh_label[7] },  /* Resume */
    { 0xAB0B9CUL, 0x00C957D8UL, "\x41\x63\x63\x65\x70\x74", ui_zh_label[8] },  /* Accept */
    { 0xAB0BA4UL, 0x00C93310UL, "\x42\x61\x63\x6b", ui_zh_label[9] },  /* Back */
    { 0xAB0BACUL, 0x00C957D0UL, "\x44\x65\x63\x6c\x69\x6e\x65", ui_zh_label[10] },  /* Decline */
    { 0xAB0BB4UL, 0x00C957CCUL, "\x59\x65\x73", ui_zh_label[11] },  /* Yes */
    { 0xAB0BBCUL, 0x00C957C8UL, "\x4e\x6f", ui_zh_label[12] },  /* No */
    { 0xAB0BC4UL, 0x00C957C4UL, "\x4f\x4b", ui_zh_label[13] },  /* OK */
    { 0xAB0BCCUL, 0x00C957BCUL, "\x43\x61\x6e\x63\x65\x6c", ui_zh_label[14] },  /* Cancel */
    { 0xAB0BD4UL, 0x00C763E4UL, "\x4f\x6e", ui_zh_label[15] },  /* On */
    { 0xAB0BDCUL, 0x00C763E0UL, "\x4f\x66\x66", ui_zh_label[16] },  /* Off */
    { 0xAB0BE4UL, 0x00C957A8UL, "\x52\x65\x73\x65\x74\x20\x54\x6f\x20\x44\x65\x66\x61\x75\x6c\x74\x73", ui_zh_label[17] },  /* Reset To Defaults */
    { 0xAB0BECUL, 0x00C95798UL, "\x56\x69\x64\x65\x6f\x20\x53\x65\x74\x74\x69\x6e\x67\x73", ui_zh_label[18] },  /* Video Settings */
    { 0xAB0BF4UL, 0x00C95784UL, "\x53\x63\x72\x65\x65\x6e\x20\x52\x65\x73\x6f\x6c\x75\x74\x69\x6f\x6e", ui_zh_label[19] },  /* Screen Resolution */
    { 0xAB0BFCUL, 0x00C95774UL, "\x52\x65\x66\x72\x65\x73\x68\x20\x52\x61\x74\x65", ui_zh_label[20] },  /* Refresh Rate */
    { 0xAB0C04UL, 0x00C95764UL, "\x56\x65\x72\x74\x69\x63\x61\x6c\x20\x53\x79\x6e\x63", ui_zh_label[21] },  /* Vertical Sync */
    { 0xAB0C0CUL, 0x00C95754UL, "\x41\x73\x70\x65\x63\x74\x20\x52\x61\x74\x69\x6f", ui_zh_label[22] },  /* Aspect Ratio */
    { 0xAB0C14UL, 0x00C95740UL, "\x45\x6e\x68\x61\x6e\x63\x65\x64\x20\x47\x72\x61\x70\x68\x69\x63\x73", ui_zh_label[23] },  /* Enhanced Graphics */
    { 0xAB0C1CUL, 0x00C95730UL, "\x46\x72\x6f\x6d\x20\x53\x63\x72\x65\x65\x6e\x2d\x52\x65\x73", ui_zh_label[24] },  /* From Screen-Res */
    { 0xAB0C24UL, 0x00C95718UL, "\x55\x73\x65\x20\x63\x75\x72\x72\x65\x6e\x74\x20\x73\x65\x74\x74\x69\x6e\x67\x73", ui_zh_label[25] },  /* Use current settings */
    { 0xAB0C2CUL, 0x00C95708UL, "\x54\x65\x78\x74\x75\x72\x65\x20\x51\x75\x61\x6c\x69\x74\x79", ui_zh_label[26] },  /* Texture Quality */
    { 0xAB0C34UL, 0x00C95700UL, "\x52\x65\x76\x65\x72\x74", ui_zh_label[27] },  /* Revert */
    { 0xAB0C3CUL, 0x00C956C4UL, "\x59\x6f\x75\x20\x6d\x75\x73\x74\x20\x72\x65\x73\x74\x61\x72\x74\x20\x74\x68\x65\x20\x67\x61\x6d\x65\x20\x66\x6f\x72\x20\x74\x68\x65\x73\x65\x20\x63\x68\x61\x6e\x67\x65\x73\x20\x74\x6f\x20\x74\x61\x6b\x65\x20\x65\x66\x66\x65\x63\x74\x21", ui_zh_label[28] },  /* You must restart the game for these changes to take effect! */
    { 0xAB0C44UL, 0x00C956B0UL, "\x45\x66\x66\x65\x63\x74\x73\x20\x53\x65\x74\x74\x69\x6e\x67\x73", ui_zh_label[29] },  /* Effects Settings */
    { 0xAB0C4CUL, 0x00C95A6CUL, "\x46\x53\x41\x41", ui_zh_label[30] },  /* FSAA */
    { 0xAB0C54UL, 0x00C956A0UL, "\x45\x78\x74\x65\x72\x6e\x61\x6c\x6c\x79\x20\x53\x65\x74", ui_zh_label[31] },  /* Externally Set */
    { 0xAB0C5CUL, 0x00C95698UL, "\x53\x68\x61\x64\x6f\x77\x73", ui_zh_label[32] },  /* Shadows */
    { 0xAB0C64UL, 0x00C95690UL, "\x42\x6c\x6f\x6f\x6d", ui_zh_label[33] },  /* Bloom */
    { 0xAB0C6CUL, 0x00C95680UL, "\x44\x65\x70\x74\x68\x20\x6f\x66\x20\x46\x69\x65\x6c\x64", ui_zh_label[34] },  /* Depth of Field */
    { 0xAB0C74UL, 0x00C95674UL, "\x53\x70\x65\x65\x64\x20\x42\x6c\x75\x72", ui_zh_label[35] },  /* Speed Blur */
    { 0xAB0C7CUL, 0x00C9565CUL, "\x44\x79\x6e\x61\x6d\x69\x63\x20\x4c\x69\x67\x68\x74\x20\x51\x75\x61\x6c\x69\x74\x79", ui_zh_label[36] },  /* Dynamic Light Quality */
    { 0xAB0C84UL, 0x00C95654UL, "\x45\x64\x67\x65\x20\x41\x41", ui_zh_label[37] },  /* Edge AA */
    { 0xAB0C8CUL, 0x00C95640UL, "\x41\x6d\x62\x69\x65\x6e\x74\x20\x4f\x63\x63\x6c\x75\x73\x69\x6f\x6e", ui_zh_label[38] },  /* Ambient Occlusion */
    { 0xAB0C94UL, 0x00C9562CUL, "\x53\x68\x6f\x77\x20\x47\x61\x6d\x65\x20\x43\x6f\x6e\x74\x72\x6f\x6c\x73", ui_zh_label[39] },  /* Show Game Controls */
    { 0xAB0CA4UL, 0x00C95824UL, "\x51\x75\x69\x74", ui_zh_label[0] },  /* Quit */
    { 0xAB0CACUL, 0x00C95814UL, "\x51\x75\x69\x74\x20\x74\x6f\x20\x57\x69\x6e\x64\x6f\x77\x73", ui_zh_label[1] },  /* Quit to Windows */
    { 0xAB0CB4UL, 0x00C95800UL, "\x51\x75\x69\x74\x20\x74\x6f\x20\x44\x65\x6d\x6f\x73\x20\x4d\x65\x6e\x75", ui_zh_label[2] },  /* Quit to Demos Menu */
    { 0xAB0CBCUL, 0x00C957F0UL, "\x52\x65\x74\x75\x72\x6e\x20\x74\x6f\x20\x67\x61\x6d\x65", ui_zh_label[3] },  /* Return to game */
    { 0xAB0CC4UL, 0x00C9A98CUL, "\x4c\x6f\x77", ui_zh_label[4] },  /* Low */
    { 0xAB0CCCUL, 0x00C957E8UL, "\x4d\x65\x64\x69\x75\x6d", ui_zh_label[5] },  /* Medium */
    { 0xAB0CD4UL, 0x00C9A984UL, "\x48\x69\x67\x68", ui_zh_label[6] },  /* High */
    { 0xAB0CDCUL, 0x00C957E0UL, "\x52\x65\x73\x75\x6d\x65", ui_zh_label[7] },  /* Resume */
    { 0xAB0CE4UL, 0x00C957D8UL, "\x41\x63\x63\x65\x70\x74", ui_zh_label[8] },  /* Accept */
    { 0xAB0CECUL, 0x00C957D0UL, "\x44\x65\x63\x6c\x69\x6e\x65", ui_zh_label[10] },  /* Decline */
    { 0xAB0CF4UL, 0x00C93310UL, "\x42\x61\x63\x6b", ui_zh_label[9] },  /* Back */
    { 0xAB0CFCUL, 0x00C957CCUL, "\x59\x65\x73", ui_zh_label[11] },  /* Yes */
    { 0xAB0D04UL, 0x00C957C8UL, "\x4e\x6f", ui_zh_label[12] },  /* No */
    { 0xAB0D0CUL, 0x00C957C4UL, "\x4f\x4b", ui_zh_label[13] },  /* OK */
    { 0xAB0D14UL, 0x00C957BCUL, "\x43\x61\x6e\x63\x65\x6c", ui_zh_label[14] },  /* Cancel */
    { 0xAB0D1CUL, 0x00C763E4UL, "\x4f\x6e", ui_zh_label[15] },  /* On */
    { 0xAB0D24UL, 0x00C763E0UL, "\x4f\x66\x66", ui_zh_label[16] },  /* Off */
    { 0xAB0D2CUL, 0x00C957A8UL, "\x52\x65\x73\x65\x74\x20\x54\x6f\x20\x44\x65\x66\x61\x75\x6c\x74\x73", ui_zh_label[17] },  /* Reset To Defaults */
    { 0xAB0D34UL, 0x00C95798UL, "\x56\x69\x64\x65\x6f\x20\x53\x65\x74\x74\x69\x6e\x67\x73", ui_zh_label[18] },  /* Video Settings */
    { 0xAB0D3CUL, 0x00C95784UL, "\x53\x63\x72\x65\x65\x6e\x20\x52\x65\x73\x6f\x6c\x75\x74\x69\x6f\x6e", ui_zh_label[19] },  /* Screen Resolution */
    { 0xAB0D44UL, 0x00C95774UL, "\x52\x65\x66\x72\x65\x73\x68\x20\x52\x61\x74\x65", ui_zh_label[20] },  /* Refresh Rate */
    { 0xAB0D4CUL, 0x00C95764UL, "\x56\x65\x72\x74\x69\x63\x61\x6c\x20\x53\x79\x6e\x63", ui_zh_label[21] },  /* Vertical Sync */
    { 0xAB0D54UL, 0x00C95754UL, "\x41\x73\x70\x65\x63\x74\x20\x52\x61\x74\x69\x6f", ui_zh_label[22] },  /* Aspect Ratio */
    { 0xAB0D5CUL, 0x00C95740UL, "\x45\x6e\x68\x61\x6e\x63\x65\x64\x20\x47\x72\x61\x70\x68\x69\x63\x73", ui_zh_label[23] },  /* Enhanced Graphics */
    { 0xAB0D64UL, 0x00C95730UL, "\x46\x72\x6f\x6d\x20\x53\x63\x72\x65\x65\x6e\x2d\x52\x65\x73", ui_zh_label[24] },  /* From Screen-Res */
    { 0xAB0D6CUL, 0x00C95718UL, "\x55\x73\x65\x20\x63\x75\x72\x72\x65\x6e\x74\x20\x73\x65\x74\x74\x69\x6e\x67\x73", ui_zh_label[25] },  /* Use current settings */
    { 0xAB0D74UL, 0x00C95708UL, "\x54\x65\x78\x74\x75\x72\x65\x20\x51\x75\x61\x6c\x69\x74\x79", ui_zh_label[26] },  /* Texture Quality */
    { 0xAB0D7CUL, 0x00C95700UL, "\x52\x65\x76\x65\x72\x74", ui_zh_label[27] },  /* Revert */
    { 0xAB0D84UL, 0x00C956C4UL, "\x59\x6f\x75\x20\x6d\x75\x73\x74\x20\x72\x65\x73\x74\x61\x72\x74\x20\x74\x68\x65\x20\x67\x61\x6d\x65\x20\x66\x6f\x72\x20\x74\x68\x65\x73\x65\x20\x63\x68\x61\x6e\x67\x65\x73\x20\x74\x6f\x20\x74\x61\x6b\x65\x20\x65\x66\x66\x65\x63\x74\x21", ui_zh_label[28] },  /* You must restart the game for these changes to take effect! */
    { 0xAB0D8CUL, 0x00C956B0UL, "\x45\x66\x66\x65\x63\x74\x73\x20\x53\x65\x74\x74\x69\x6e\x67\x73", ui_zh_label[29] },  /* Effects Settings */
    { 0xAB0D94UL, 0x00C95A6CUL, "\x46\x53\x41\x41", ui_zh_label[30] },  /* FSAA */
    { 0xAB0D9CUL, 0x00C956A0UL, "\x45\x78\x74\x65\x72\x6e\x61\x6c\x6c\x79\x20\x53\x65\x74", ui_zh_label[31] },  /* Externally Set */
    { 0xAB0DA4UL, 0x00C95698UL, "\x53\x68\x61\x64\x6f\x77\x73", ui_zh_label[32] },  /* Shadows */
    { 0xAB0DACUL, 0x00C95690UL, "\x42\x6c\x6f\x6f\x6d", ui_zh_label[33] },  /* Bloom */
    { 0xAB0DB4UL, 0x00C95680UL, "\x44\x65\x70\x74\x68\x20\x6f\x66\x20\x46\x69\x65\x6c\x64", ui_zh_label[34] },  /* Depth of Field */
    { 0xAB0DBCUL, 0x00C95674UL, "\x53\x70\x65\x65\x64\x20\x42\x6c\x75\x72", ui_zh_label[35] },  /* Speed Blur */
    { 0xAB0DC4UL, 0x00C9565CUL, "\x44\x79\x6e\x61\x6d\x69\x63\x20\x4c\x69\x67\x68\x74\x20\x51\x75\x61\x6c\x69\x74\x79", ui_zh_label[36] },  /* Dynamic Light Quality */
    { 0xAB0DCCUL, 0x00C95654UL, "\x45\x64\x67\x65\x20\x41\x41", ui_zh_label[37] },  /* Edge AA */
    { 0xAB0DD4UL, 0x00C95640UL, "\x41\x6d\x62\x69\x65\x6e\x74\x20\x4f\x63\x63\x6c\x75\x73\x69\x6f\x6e", ui_zh_label[38] },  /* Ambient Occlusion */
    { 0xAB0DDCUL, 0x00C9562CUL, "\x53\x68\x6f\x77\x20\x47\x61\x6d\x65\x20\x43\x6f\x6e\x74\x72\x6f\x6c\x73", ui_zh_label[39] },  /* Show Game Controls */
};
#define UI_PATCH_COUNT 80

#endif /* UI_PATCH_H */
