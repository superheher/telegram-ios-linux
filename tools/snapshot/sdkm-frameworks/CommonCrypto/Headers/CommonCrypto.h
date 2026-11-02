/* Authored for the SDK-free sysroot (not Apple's file): the CommonCrypto public API subset
   the app uses, faithful to the real header (CommonCrypto is stable public API). */
#ifndef COMMONCRYPTO_H
#define COMMONCRYPTO_H
#include <stdint.h>
#include <stddef.h>

enum {
    CC_SHA256_DIGEST_LENGTH = 32
};

typedef uint32_t CCHmacAlgorithm;
enum {
    kCCHmacAlgSHA1 = 1,
    kCCHmacAlgMD5 = 2,
    kCCHmacAlgSHA256 = 3,
    kCCHmacAlgSHA384 = 4,
    kCCHmacAlgSHA512 = 5,
    kCCHmacAlgSHA224 = 6
};

void CCHmac(CCHmacAlgorithm algorithm, const void *key, size_t keyLength,
            const void *data, size_t dataLength, void *macOut);

#endif
