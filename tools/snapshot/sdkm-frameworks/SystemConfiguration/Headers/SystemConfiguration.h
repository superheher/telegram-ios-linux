/* Authored for the SDK-free sysroot (not Apple's file): SCNetworkReachability public API
   subset the app uses, faithful to the real header. */
#ifndef SYSTEMCONFIGURATION_H
#define SYSTEMCONFIGURATION_H
#include <CoreFoundation/CoreFoundation.h>
#include <sys/socket.h>

typedef struct __SCNetworkReachability *SCNetworkReachabilityRef;

typedef void (*SCNetworkReachabilityCallback)(SCNetworkReachabilityRef target,
                                              uint32_t flags, void *info);

enum {
    kSCNetworkReachabilityFlagsTransientConnection = 1 << 0,
    kSCNetworkReachabilityFlagsReachable = 1 << 1,
    kSCNetworkReachabilityFlagsConnectionRequired = 1 << 2,
    kSCNetworkReachabilityFlagsConnectionOnTraffic = 1 << 3,
    kSCNetworkReachabilityFlagsInterventionRequired = 1 << 4,
    kSCNetworkReachabilityFlagsConnectionOnDemand = 1 << 5,
    kSCNetworkReachabilityFlagsIsLocalAddress = 1 << 16,
    kSCNetworkReachabilityFlagsIsDirect = 1 << 17,
    kSCNetworkReachabilityFlagsIsWWAN = 1 << 18
};

SCNetworkReachabilityRef SCNetworkReachabilityCreateWithName(CFAllocatorRef allocator,
                                                             const char *nodename);
SCNetworkReachabilityRef SCNetworkReachabilityCreateWithAddress(CFAllocatorRef allocator,
                                                                const struct sockaddr *address);
int SCNetworkReachabilityGetFlags(SCNetworkReachabilityRef target, uint32_t *flags);
int SCNetworkReachabilitySetCallback(SCNetworkReachabilityRef target,
                                     SCNetworkReachabilityCallback callback, void *info);
int SCNetworkReachabilityScheduleWithRunLoop(SCNetworkReachabilityRef target,
                                             CFRunLoopRef runLoop, CFStringRef runLoopMode);
int SCNetworkReachabilityUnscheduleFromRunLoop(SCNetworkReachabilityRef target,
                                               CFRunLoopRef runLoop, CFStringRef runLoopMode);

#endif
