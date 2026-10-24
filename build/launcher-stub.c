/*
 * GrabIt Downloader — Mac başlatıcı (Mach-O).
 *
 * Apple imzası ve onayı (notarization) için uygulamanın ana dosyası gerçek bir
 * program olmalı. Bu küçük program sadece Contents/Resources/launcher.sh betiğini
 * aynı süreç içinde (exec) çalıştırır; asıl iş o betikte yapılır.
 */
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char exe[PATH_MAX], real[PATH_MAX], script[PATH_MAX + 64];
    uint32_t size = sizeof(exe);

    if (_NSGetExecutablePath(exe, &size) != 0 || realpath(exe, real) == NULL) {
        fprintf(stderr, "GrabIt: program yolu bulunamadı\n");
        return 1;
    }
    /* .../GrabIt Downloader.app/Contents/MacOS/GrabIt -> .../Contents/Resources/launcher.sh */
    snprintf(script, sizeof(script), "%s/../Resources/launcher.sh", dirname(real));

    execl("/bin/bash", "bash", script, (char *)NULL);
    perror("GrabIt: başlatıcı çalıştırılamadı");
    return 1;
}
