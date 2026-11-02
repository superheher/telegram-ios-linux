/* Authored for the SDK-free sysroot (not Apple's file): the WebKit API subset the app's
   WEB proxy carrier uses, faithful to the public API (signatures mirror the real headers;
   delegate methods declared @optional as in the real protocol). APIs newer than the
   sdk-free baseline (media-capture permission, open panel, downloads) are declared without
   availability markers — the app's own @available annotations stay authoritative. */
#ifndef WEBKIT_H
#define WEBKIT_H
#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

typedef NS_ENUM(NSInteger, WKUserScriptInjectionTime) {
    WKUserScriptInjectionTimeAtDocumentStart,
    WKUserScriptInjectionTimeAtDocumentEnd,
};

typedef NS_ENUM(NSInteger, WKNavigationActionPolicy) {
    WKNavigationActionPolicyCancel,
    WKNavigationActionPolicyAllow,
} __attribute__((swift_name("WKNavigationActionPolicy")));

typedef NS_ENUM(NSInteger, WKNavigationResponsePolicy) {
    WKNavigationResponsePolicyCancel,
    WKNavigationResponsePolicyAllow,
};

typedef NS_ENUM(NSInteger, WKPermissionDecision) {
    WKPermissionDecisionGrant,
    WKPermissionDecisionDeny,
    WKPermissionDecisionPrompt,
};

typedef NS_ENUM(NSInteger, WKMediaCaptureType) {
    WKMediaCaptureTypeCamera,
    WKMediaCaptureTypeMicrophone,
    WKMediaCaptureTypeCameraAndMicrophone,
    WKMediaCaptureTypeDisplay,
};

typedef NS_OPTIONS(NSUInteger, WKAudiovisualMediaTypes) {
    WKAudiovisualMediaTypeNone = 0,
    WKAudiovisualMediaTypeAudio = 1 << 0,
    WKAudiovisualMediaTypeVideo = 1 << 1,
    WKAudiovisualMediaTypeAll = 1 << 31,
};

@class WKWebView;
@class WKWebViewConfiguration;
@class WKUserScript;
@class WKUserContentController;
@protocol WKNavigationDelegate;
@protocol WKUIDelegate;
@class WKContentWorld;
@interface WKContentWorld : NSObject
@property(class, readonly, strong) WKContentWorld *pageWorld __attribute__((swift_name("page")));
@property(class, readonly, strong) WKContentWorld *defaultWorld;
@end

@interface WKSecurityOrigin : NSObject <NSCopying>
@property (readonly, copy) NSString *protocol;
@property (readonly, copy) NSString *host;
@property (readonly) NSInteger port;
@end

@interface WKFrameInfo : NSObject <NSCopying>
@property (readonly, nonatomic, getter=isMainFrame) BOOL mainFrame;
@property (readonly, copy) WKSecurityOrigin *securityOrigin;
@end

@interface WKUserScript : NSObject <NSCopying>
- (instancetype)initWithSource:(NSString *)source injectionTime:(WKUserScriptInjectionTime)injectionTime forMainFrameOnly:(BOOL)forMainFrameOnly;
- (instancetype)initWithSource:(NSString *)source injectionTime:(WKUserScriptInjectionTime)injectionTime forMainFrameOnly:(BOOL)forMainFrameOnly inContentWorld:(WKContentWorld *)contentWorld;
@property (readonly, copy) NSString *source;
@property (readonly) WKUserScriptInjectionTime injectionTime;
@property (readonly, getter=isForMainFrameOnly) BOOL forMainFrameOnly;
@end

@interface WKScriptMessage : NSObject
@property (readonly, strong) WKFrameInfo *frameInfo;
@property (readonly, copy) id body;
@property (readonly, copy) NSString *name;
@property (nullable, readonly, weak) WKWebView *webView;
@end

@protocol WKScriptMessageHandler <NSObject>
@optional
- (void)userContentController:(WKUserContentController *)userContentController didReceiveScriptMessage:(WKScriptMessage *)message;
@end

@interface WKUserContentController : NSObject
- (instancetype)init;
@property (readonly, copy) NSArray<WKUserScript *> *userScripts;
- (void)addUserScript:(WKUserScript *)userScript;
- (void)removeAllUserScripts;
- (void)addScriptMessageHandler:(id <WKScriptMessageHandler>)scriptMessageHandler name:(NSString *)name;
- (void)addScriptMessageHandler:(id <WKScriptMessageHandler>)scriptMessageHandler contentWorld:(WKContentWorld *)world name:(NSString *)name;
- (void)removeScriptMessageHandlerForName:(NSString *)name;
- (void)removeScriptMessageHandlerForName:(NSString *)name contentWorld:(WKContentWorld *)world;
@end

@class WKPreferences;
@class WKWebsiteDataStore;
@class WKProcessPool;
@interface WKWebViewConfiguration : NSObject <NSCopying, NSSecureCoding>
- (instancetype)init;
@property (nullable, nonatomic, strong) WKProcessPool *processPool;
@property (nonatomic, strong) WKPreferences *preferences;
@property (nonatomic, strong) WKUserContentController *userContentController;
@property (nonatomic, strong) WKWebsiteDataStore *websiteDataStore;
@property (nonatomic) BOOL allowsAirPlayForMediaPlayback;
@property (nonatomic) BOOL allowsPictureInPictureMediaPlayback;
@property (nonatomic) BOOL allowsInlineMediaPlayback;
@property (nonatomic) WKAudiovisualMediaTypes mediaTypesRequiringUserActionForPlayback;
@end

@interface WKPreferences : NSObject <NSCopying, NSSecureCoding>
@property (nonatomic) BOOL javaScriptCanOpenWindowsAutomatically;
@property (nonatomic) BOOL isElementFullscreenEnabled;
@end

@interface WKWebsiteDataStore : NSObject <NSSecureCoding>
+ (WKWebsiteDataStore *)defaultDataStore;
+ (WKWebsiteDataStore *)nonPersistentDataStore __attribute__((swift_name("nonPersistent()")));
@end

@class WKNavigation;
@class WKNavigationAction;
@class WKNavigationResponse;
@interface WKWebView : UIView
- (instancetype)initWithFrame:(CGRect)frame configuration:(nullable WKWebViewConfiguration *)configuration;
@property (nullable, nonatomic, weak) id <WKNavigationDelegate> navigationDelegate;
@property (nullable, nonatomic, weak) id <WKUIDelegate> uiDelegate;
@property (nullable, readonly, copy) NSURL *URL;
@property (readonly, strong) WKWebViewConfiguration *configuration;
- (nullable WKNavigation *)loadRequest:(NSURLRequest *)request;
- (void)stopLoading;
- (void)evaluateJavaScript:(NSString *)javaScriptString completionHandler:(void (^ _Nullable)(id _Nullable result, NSError * _Nullable error))completionHandler;
- (void)callAsyncJavaScript:(NSString *)functionBody arguments:(nullable NSDictionary *)arguments inFrame:(nullable WKFrameInfo *)frame inContentWorld:(WKContentWorld *)world completionHandler:(void (^ _Nullable)(_Nullable id result, NSError * _Nullable error))completionHandler NS_REFINED_FOR_SWIFT;
@end

@interface WKNavigation : NSObject
@end

@interface WKNavigationAction : NSObject
@property (nullable, readonly, strong) WKFrameInfo *targetFrame;
@property (readonly, copy) NSURLRequest *request;
@property (readonly, nonatomic, getter=shouldPerformDownload) BOOL performDownload;
@end

@interface WKNavigationResponse : NSObject
@property (readonly, nonatomic, getter=isForMainFrame) BOOL forMainFrame;
@property (readonly, copy) NSURLResponse *response;
@end

@interface WKDownload : NSObject
- (void)cancel:(void (^ _Nullable)(NSData *resumeData))completionHandler;
@end

@interface WKWindowFeatures : NSObject
@end

@interface WKOpenPanelParameters : NSObject
@end

@protocol WKNavigationDelegate <NSObject>
@optional
- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)navigationAction decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler;
- (void)webView:(WKWebView *)webView decidePolicyForNavigationResponse:(WKNavigationResponse *)navigationResponse decisionHandler:(void (^)(WKNavigationResponsePolicy))decisionHandler;
- (void)webView:(WKWebView *)webView didReceiveAuthenticationChallenge:(NSURLAuthenticationChallenge *)challenge completionHandler:(void (^)(NSURLSessionAuthChallengeDisposition disposition, NSURLCredential * _Nullable credential))completionHandler;
- (void)webView:(WKWebView *)webView didStartProvisionalNavigation:(WKNavigation *)navigation;
- (void)webView:(WKWebView *)webView didReceiveServerRedirectForProvisionalNavigation:(WKNavigation *)navigation;
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error;
- (void)webView:(WKWebView *)webView didCommitNavigation:(WKNavigation *)navigation;
- (void)webView:(WKWebView *)webView didFinishNavigation:(WKNavigation *)navigation;
- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error;
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView;
- (void)webView:(WKWebView *)webView navigationAction:(WKNavigationAction *)navigationAction didBecomeDownload:(WKDownload *)download;
- (void)webView:(WKWebView *)webView navigationResponse:(WKNavigationResponse *)navigationResponse didBecomeDownload:(WKDownload *)download;
@end

@protocol WKUIDelegate <NSObject>
@optional
- (nullable WKWebView *)webView:(WKWebView *)webView createWebViewWithConfiguration:(WKWebViewConfiguration *)configuration forNavigationAction:(WKNavigationAction *)navigationAction windowFeatures:(WKWindowFeatures *)windowFeatures;
- (void)webView:(WKWebView *)webView runJavaScriptAlertPanelWithMessage:(NSString *)message initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(void))completionHandler;
- (void)webView:(WKWebView *)webView runJavaScriptConfirmPanelWithMessage:(NSString *)message initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(BOOL result))completionHandler;
- (void)webView:(WKWebView *)webView runJavaScriptTextInputPanelWithPrompt:(NSString *)prompt defaultText:(nullable NSString *)defaultText initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(NSString * _Nullable result))completionHandler;
- (void)webView:(WKWebView *)webView requestMediaCapturePermissionForOrigin:(WKSecurityOrigin *)origin initiatedByFrame:(WKFrameInfo *)frame type:(WKMediaCaptureType)type decisionHandler:(void (^)(WKPermissionDecision decision))decisionHandler;
- (void)webView:(WKWebView *)webView requestDeviceOrientationAndMotionPermissionForOrigin:(WKSecurityOrigin *)origin initiatedByFrame:(WKFrameInfo *)frame decisionHandler:(void (^)(WKPermissionDecision decision))decisionHandler;
- (void)webView:(WKWebView *)webView requestGeolocationPermissionForOrigin:(WKSecurityOrigin *)origin initiatedByFrame:(WKFrameInfo *)frame decisionHandler:(void (^)(WKPermissionDecision decision))decisionHandler;
- (void)webView:(WKWebView *)webView runOpenPanelWithParameters:(WKOpenPanelParameters *)parameters initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(NSArray<NSURL *> * _Nullable URLs))completionHandler;
@end

NS_ASSUME_NONNULL_END
#endif
