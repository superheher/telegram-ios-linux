/* Authored for the SDK-free sysroot (not Apple's file): the LinkPresentation subset the app
   uses. The provider's fetch is marked unavailable-in-shim: it would hit the network through
   the real framework; the call sites handle the error path. */
#ifndef LINKPRESENTATION_H
#define LINKPRESENTATION_H
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface LPLinkMetadata : NSObject
@property (nullable, readonly, copy) NSURL *URL;
@end

__attribute__((swift_name("LPLoaderStatus"))) typedef NS_ENUM(NSInteger, LPLoaderStatus) {
    LPLoaderStatusStarted,
    LPLoaderStatusLoaded,
    LPLoaderStatusCancelled,
    LPLoaderStatusFailed,
};

@interface LPMetadataProvider : NSObject
@property (nonatomic) BOOL shouldFetchSubresources;
- (void)startFetchingMetadataForURL:(NSURL *)URL
                  completionHandler:(void (^)(LPLinkMetadata * _Nullable metadata, NSError * _Nullable error))completionHandler;
@end

NS_ASSUME_NONNULL_END
#endif
