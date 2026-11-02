/* Authored for the SDK-free sysroot (not Apple's file): the CoreTelephony subset the app
   uses (radio access technology reporting), faithful to the public API. */
#ifndef CORETELEPHONY_H
#define CORETELEPHONY_H
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyGPRS;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyEdge;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyWCDMA;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyHSDPA;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyHSUPA;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyCDMA1x;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyCDMAEVDORev0;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyCDMAEVDORevA;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyCDMAEVDORevB;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyeHRPD;
FOUNDATION_EXPORT NSString * const CTRadioAccessTechnologyLTE;

FOUNDATION_EXPORT NSString * const CTServiceRadioAccessTechnologyDidChangeNotification;

__attribute__((swift_name("NSNotification.Name"))) @interface CoreTelephonyNotificationName
+ (instancetype)CTServiceRadioAccessTechnologyDidChange;
@end

@interface CTTelephonyNetworkInfo : NSObject
@property (nullable, readonly, copy) NSDictionary<NSString *, NSString *> *serviceCurrentRadioAccessTechnology;
@end

NS_ASSUME_NONNULL_END
#endif
