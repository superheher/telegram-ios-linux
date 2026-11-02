/* Authored for the SDK-free sysroot (not Apple's file): SecRandom subset used by the app.
   The real SecRandomCopyBytes reads the kernel CSPRNG; this module's headers are compile-time
   only (linking happens against the real framework's symbols on device — Phase 4 records it). */
#ifndef SECURITY_H
#define SECURITY_H
#include <stddef.h>
#include <stdint.h>

enum {
    errSecSuccess = 0,
};

typedef struct OpaqueSecRandomRef *SecRandomRef;
static const SecRandomRef kSecRandomDefault = 0; /* imported by Swift as a global let */

int SecRandomCopyBytes(SecRandomRef rnd, size_t count, void *bytes);

#endif
