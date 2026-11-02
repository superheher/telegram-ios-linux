#include <limits.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <errno.h>
#pragma once
// Omarchy SDK-free Foundation subset: written from the public behaviour and names of the classes, not copied
// from any SDK. Grows as builds fail.
#if __has_feature(modules)
@import ObjectiveC;
#else
#import <objc/NSObject.h>
#import <objc/NSObjCRuntime.h>
#endif
#import <CoreGraphics/CoreGraphics.h>
#import <CoreFoundation/CoreFoundation.h>
#import <Security/Security.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <sys/cdefs.h>
#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <sys/param.h>
#include <os/log.h>
#include <time.h>

#define NS_ASSUME_NONNULL_BEGIN _Pragma("clang assume_nonnull begin")
#define NS_ASSUME_NONNULL_END _Pragma("clang assume_nonnull end")
/* Anonymous and named enums: RN 0.87 headers use `NS_ENUM(NSInteger){...}`. */
#define _NSEO_PICK(_1, _2, _3, ...) _3
#define _NSEO_1(_type) enum __attribute__((enum_extensibility(closed))) : _type
#define _NSEO_2(_type, _name) enum __attribute__((enum_extensibility(closed))) _name : _type _name; enum __attribute__((enum_extensibility(closed))) _name : _type
#include <CoreFoundation/CFAvailability.h>
#define NS_ENUM(_type, _name) CF_ENUM(_type, _name)
#define NS_OPTIONS(_type, _name) CF_OPTIONS(_type, _name)
#define NS_CLOSED_ENUM(...) _NSEO_PICK(__VA_ARGS__, _NSEO_2, _NSEO_1)(__VA_ARGS__)
#define NS_TYPED_ENUM
#define NS_TYPED_EXTENSIBLE_ENUM
#define NS_STRING_ENUM
#define NS_EXTENSIBLE_STRING_ENUM
#define NS_SWIFT_NAME(x) __attribute__((swift_name(#x)))
#define NS_REFINED_FOR_SWIFT __attribute__((swift_private))
#define NS_SWIFT_UNAVAILABLE(msg) __attribute__((availability(swift, unavailable, message = msg)))
#define NS_NOESCAPE __attribute__((noescape))
#define NS_REQUIRES_SUPER __attribute__((objc_requires_super))
#define NS_REQUIRES_NIL_TERMINATION __attribute__((sentinel(0, 1)))
#define NS_SWIFT_SENDABLE
#define NS_SWIFT_UI_ACTOR
#define NS_SWIFT_NONISOLATED
#define NS_EXTENSION_UNAVAILABLE(msg)
#define NS_EXTENSION_UNAVAILABLE_IOS(msg)
#define NS_UNAVAILABLE __attribute__((unavailable))
#define NS_DEPRECATED_IOS(...)
#define NS_FORMAT_FUNCTION(F, A) __attribute__((format(__NSString__, F, A)))
#define NS_FORMAT_ARGUMENT(A) __attribute__((format_arg(A)))
#define FOUNDATION_EXPORT extern
#define FOUNDATION_EXTERN extern
#define NS_INLINE static inline
#define NS_RETURNS_RETAINED __attribute__((ns_returns_retained))
#define NS_RETURNS_NOT_RETAINED __attribute__((ns_returns_not_retained))
#define NS_RETURNS_INNER_POINTER __attribute__((objc_returns_inner_pointer))
#define NS_VALID_UNTIL_END_OF_SCOPE __attribute__((objc_precise_lifetime))

@class NSString, NSData, NSArray<ObjectType>, NSDictionary<KeyType, ObjectType>, NSSet<ObjectType>, NSURL, NSError,
    NSNumber, NSBundle, NSCoder, NSDate, NSLocale, NSTimeZone, NSUUID, NSNotification, NSOperationQueue,
    NSURLSession, NSURLRequest, NSThread, NSRunLoop, NSIndexSet, NSIndexPath, NSCharacterSet, NSAttributedString,
    NSMutableString, NSMutableData, NSMutableArray<ObjectType>, NSMutableDictionary,
    NSMutableSet<ObjectType>, NSFileManager, NSLock;

typedef NSString *NSNotificationName __attribute__((swift_wrapper(struct)));
typedef NSString *NSErrorDomain __attribute__((swift_bridged_typedef));
typedef NSString *NSRunLoopMode __attribute__((swift_wrapper(struct)));
typedef NSString *NSErrorUserInfoKey __attribute__((swift_bridged_typedef));
typedef double NSTimeInterval;
typedef uint8_t UInt8; typedef int8_t SInt8; typedef uint16_t UInt16; typedef int16_t SInt16;
typedef uint32_t UInt32; typedef int32_t SInt32; typedef uint64_t UInt64; typedef int64_t SInt64;
typedef int32_t OSStatus; typedef _Bool Boolean; /* imports as Swift Bool, as on Apple's SDK */
typedef struct _NSRange { NSInteger location; NSInteger length; } NSRange;
typedef NSRange *NSRangePointer;
typedef struct { NSInteger majorVersion; NSInteger minorVersion; NSInteger patchVersion; } NSOperatingSystemVersion;
typedef NS_ENUM(NSInteger, NSComparisonResult) { NSOrderedAscending = -1L, NSOrderedSame, NSOrderedDescending };
typedef NS_OPTIONS(NSUInteger, NSStringCompareOptions) {
  NSCaseInsensitiveSearch = 1, NSLiteralSearch = 2, NSBackwardsSearch = 4, NSAnchoredSearch = 8,
  NSNumericSearch = 64
} __attribute__((swift_name("NSString.CompareOptions")));
typedef NSUInteger NSStringEncoding;
enum {
  NSASCIIStringEncoding = 1, NSUTF8StringEncoding = 4, NSUnicodeStringEncoding = 10, NSUTF16StringEncoding = 10,
  NSUTF32StringEncoding = 0x8c000100
};
typedef unsigned short unichar;
enum { NSNotFound = NSIntegerMax };
static inline NSRange NSMakeRange(NSInteger loc, NSInteger len) { NSRange r; r.location = loc; r.length = len; return r; }

FOUNDATION_EXPORT NSString *NSStringFromClass(Class aClass);
FOUNDATION_EXPORT Class NSClassFromString(NSString *aClassName);
FOUNDATION_EXPORT NSString *NSStringFromSelector(SEL aSelector);
FOUNDATION_EXPORT SEL NSSelectorFromString(NSString *aSelectorName);
#define NSAssert(condition, desc, ...) assert(condition)
#define NSCAssert(condition, desc, ...) assert(condition)
#define NSParameterAssert(condition) assert(condition)
#define NSCParameterAssert(condition) assert(condition)
FOUNDATION_EXPORT void NSLog(NSString *format, ...) NS_FORMAT_FUNCTION(1, 2);
FOUNDATION_EXPORT void NSLogv(NSString *format, va_list args);

typedef struct NSFastEnumerationState {
  unsigned long state;
  id __unsafe_unretained _Nullable *_Nullable itemsPtr;
  unsigned long *_Nullable mutationsPtr;
  unsigned long extra[5];
} NSFastEnumerationState;
@protocol NSCopying
- (id)copyWithZone:(nullable struct _NSZone *)zone;
@end
@protocol NSMutableCopying
- (id)mutableCopyWithZone:(nullable struct _NSZone *)zone;
@end
@protocol NSCoding
- (void)encodeWithCoder:(NSCoder *)coder;
- (nullable instancetype)initWithCoder:(NSCoder *)coder;
@end
@protocol NSSecureCoding <NSCoding>
@property(class, readonly) BOOL supportsSecureCoding;
@end
@protocol NSFastEnumeration
- (NSInteger)countByEnumeratingWithState:(NSFastEnumerationState *)state objects:(id __unsafe_unretained _Nullable[_Nullable])buffer count:(NSInteger)len;
@end


NS_ASSUME_NONNULL_BEGIN

@interface NSObject (NSObjectFoundationAdditions)
- (NSString *)description;
- (void)performSelectorOnMainThread:(SEL)aSelector withObject:(nullable id)arg waitUntilDone:(BOOL)wait;
- (void)setValue:(nullable id)value forKey:(NSString *)key;
- (nullable id)valueForKey:(NSString *)key;
@end

@interface NSString : NSObject <NSCopying, NSMutableCopying, NSSecureCoding>
@property(readonly) NSInteger length;
@property(readonly, copy) NSString *description;
@property(readonly) NSUInteger hash;
- (unichar)characterAtIndex:(NSUInteger)index;
- (NSString *)substringFromIndex:(NSUInteger)from;
- (NSString *)substringToIndex:(NSUInteger)to;
- (NSString *)substringWithRange:(NSRange)range;
- (BOOL)isEqualToString:(NSString *)aString;
- (BOOL)hasPrefix:(NSString *)str;
- (BOOL)hasSuffix:(NSString *)str;
- (NSRange)rangeOfString:(NSString *)searchString;
- (NSComparisonResult)compare:(NSString *)string;
- (NSString *)stringByAppendingString:(NSString *)aString;
- (NSString *)stringByAppendingFormat:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
- (NSString *)lowercaseString;
- (NSString *)uppercaseString;
- (nullable const char *)UTF8String NS_RETURNS_INNER_POINTER;
- (nullable NSData *)dataUsingEncoding:(NSStringEncoding)encoding;
- (nullable instancetype)initWithData:(NSData *)data encoding:(NSStringEncoding)encoding;
- (nullable instancetype)initWithCString:(const char *)nullTerminatedCString encoding:(NSStringEncoding)encoding;
- (nullable instancetype)initWithContentsOfFile:(NSString *)path encoding:(NSStringEncoding)enc error:(NSError * _Nullable * _Nullable)error;
- (void)getCharacters:(unichar *)buffer range:(NSRange)range;
- (instancetype)initWithFormat:(NSString *)format arguments:(va_list)argList;
- (NSString *)replacingOccurrencesOfString:(NSString *)target withString:(NSString *)replacement;
- (nullable instancetype)initWithUTF8String:(const char *)nullTerminatedCString;
- (nullable NSData *)dataUsingEncoding:(NSStringEncoding)encoding allowLossyConversion:(BOOL)lossy;
- (NSArray<NSString *> *)componentsSeparatedByString:(NSString *)separator;
- (NSString *)stringByReplacingOccurrencesOfString:(NSString *)target withString:(NSString *)replacement;
@property(readonly) const char *fileSystemRepresentation NS_RETURNS_INNER_POINTER;
- (NSString *)stringByTrimmingCharactersInSet:(NSCharacterSet *)set;
@property(readonly) NSInteger integerValue;
@property(readonly) double doubleValue;
@property(readonly) BOOL boolValue;
+ (instancetype)string;
+ (instancetype)stringWithString:(NSString *)string;
+ (nullable instancetype)stringWithUTF8String:(const char *)nullTerminatedCString;
+ (instancetype)stringWithFormat:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
+ (nullable instancetype)stringWithContentsOfFile:(NSString *)path encoding:(NSStringEncoding)enc error:(NSError * _Nullable * _Nullable)error;
- (instancetype)init;
- (nullable instancetype)initWithData:(NSData *)data encoding:(NSStringEncoding)encoding;
- (nullable instancetype)initWithUTF8String:(const char *)nullTerminatedCString;
- (instancetype)initWithUTF8String:(const char *)nullTerminatedCString;
- (instancetype)initWithFormat:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
@end

@interface NSMutableString : NSString
+ (instancetype)stringWithCapacity:(NSUInteger)capacity;
- (instancetype)initWithCapacity:(NSUInteger)capacity;
- (void)appendString:(NSString *)aString;
- (void)appendFormat:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
@end

@interface NSValue : NSObject <NSCopying, NSSecureCoding>
@property(readonly) const char *objCType NS_RETURNS_INNER_POINTER;
@property(readonly) void *pointerValue;
@property(nonatomic, readonly, nullable) id nonretainedObjectValue;
+ (NSValue *)valueWithPointer:(nullable const void *)pointer;
+ (NSValue *)valueWithNonretainedObject:(nullable id)anObject;
@end

@interface NSNumber : NSValue
@property(readonly) char charValue;
@property(readonly) unsigned char unsignedCharValue;
@property(readonly) short shortValue;
@property(readonly) unsigned short unsignedShortValue;
@property(readonly) int intValue;
@property(readonly) unsigned int unsignedIntValue;
@property(readonly) long longValue;
@property(readonly) unsigned long unsignedLongValue;
@property(readonly) long long longLongValue;
@property(readonly) unsigned long long unsignedLongLongValue;
@property(readonly) float floatValue;
@property(readonly) double doubleValue;
@property(readonly) BOOL boolValue;
@property(readonly) NSInteger integerValue;
@property(readonly) NSUInteger unsignedIntegerValue;
@property(readonly, copy) NSString *stringValue;
- (BOOL)isEqualToNumber:(NSNumber *)number;
+ (NSNumber *)numberWithChar:(char)value;
+ (NSNumber *)numberWithUnsignedChar:(unsigned char)value;
+ (NSNumber *)numberWithShort:(short)value;
+ (NSNumber *)numberWithUnsignedShort:(unsigned short)value;
+ (NSNumber *)numberWithInt:(int)value;
+ (NSNumber *)numberWithUnsignedInt:(unsigned int)value;
+ (NSNumber *)numberWithLong:(long)value;
+ (NSNumber *)numberWithUnsignedLong:(unsigned long)value;
+ (NSNumber *)numberWithLongLong:(long long)value;
+ (NSNumber *)numberWithUnsignedLongLong:(unsigned long long)value;
+ (NSNumber *)numberWithFloat:(float)value;
+ (NSNumber *)numberWithDouble:(double)value;
+ (NSNumber *)numberWithBool:(BOOL)value;
+ (NSNumber *)numberWithInteger:(NSInteger)value;
+ (NSNumber *)numberWithUnsignedInteger:(NSUInteger)value;
@end

@interface NSEnumerator<ObjectType> : NSObject <NSFastEnumeration>
- (nullable ObjectType)nextObject;
@property(readonly, copy) NSArray<ObjectType> *allObjects;
@end

@interface NSData : NSObject <NSCopying, NSMutableCopying, NSSecureCoding>
- (instancetype)initWithBytes:(nullable const void *)bytes length:(NSInteger)length;
@property(readonly) NSInteger length; /* NSInteger: the Swift importer must see Int, as on Apple's SDK; the overlay's NSData subclass overrides it with Int (same ABI) */
@property(readonly) const void *bytes NS_RETURNS_INNER_POINTER;
+ (instancetype)data;
+ (nullable instancetype)dataWithContentsOfFile:(NSString *)path;
+ (instancetype)dataWithBytes:(nullable const void *)bytes length:(NSInteger)length;
+ (instancetype)dataWithBytesNoCopy:(void *)bytes length:(NSInteger)length freeWhenDone:(BOOL)b;
+ (nullable instancetype)dataWithContentsOfFile:(NSString *)path;
- (void)getBytes:(void *)buffer length:(NSInteger)length;
- (void)getBytes:(void *)buffer range:(NSRange)range;
- (NSData *)subdataWithRange:(NSRange)range;
- (BOOL)isEqualToData:(NSData *)other;
- (BOOL)writeToFile:(NSString *)path atomically:(BOOL)useAuxiliaryFile;
@end

@interface NSMutableData : NSData
@property(readonly) void *mutableBytes NS_RETURNS_INNER_POINTER;
@property NSInteger length;
+ (nullable instancetype)dataWithCapacity:(NSUInteger)aNumItems;
+ (nullable instancetype)dataWithLength:(NSInteger)length;
- (void)appendBytes:(const void *)bytes length:(NSInteger)length;
- (void)appendData:(NSData *)other;
- (void)replaceBytesInRange:(NSRange)range withBytes:(const void *)bytes length:(NSInteger)replacementLength;
- (void)setLength:(NSUInteger)length;
@end

@interface NSArray<__covariant ObjectType> : NSObject <NSCopying, NSMutableCopying, NSSecureCoding, NSFastEnumeration>
@property(readonly) NSInteger count;
@property(readonly, nullable) ObjectType firstObject;
@property(readonly, nullable) ObjectType lastObject;
- (ObjectType)objectAtIndex:(NSUInteger)index;
- (ObjectType)objectAtIndexedSubscript:(NSUInteger)idx;
- (BOOL)containsObject:(ObjectType)anObject;
- (NSUInteger)indexOfObject:(ObjectType)anObject;
- (NSArray<ObjectType> *)arrayByAddingObject:(ObjectType)anObject;
- (NSString *)componentsJoinedByString:(NSString *)separator;
- (void)enumerateObjectsUsingBlock:(void (^NS_NOESCAPE)(ObjectType obj, NSUInteger idx, BOOL *stop))block;
+ (instancetype)array;
+ (instancetype)arrayWithObject:(ObjectType)anObject;
+ (instancetype)arrayWithObjects:(const ObjectType _Nonnull[_Nonnull])objects count:(NSUInteger)cnt;
+ (instancetype)arrayWithArray:(NSArray<ObjectType> *)array;
- (instancetype)initWithArray:(NSArray<ObjectType> *)array;
@end

@interface NSMutableArray<ObjectType> : NSArray<ObjectType>
- (void)addObject:(ObjectType)anObject;
- (void)insertObject:(ObjectType)anObject atIndex:(NSUInteger)index;
- (void)removeObjectAtIndex:(NSUInteger)index;
- (void)removeObject:(ObjectType)anObject;
- (void)removeAllObjects;
- (void)addObjectsFromArray:(NSArray<ObjectType> *)otherArray;
+ (instancetype)arrayWithCapacity:(NSUInteger)numItems;
@end

@interface NSDictionary<__covariant KeyType, __covariant ObjectType> : NSObject <NSCopying, NSMutableCopying, NSSecureCoding, NSFastEnumeration>
@property(readonly) NSInteger count;
@property(readonly, copy) NSArray<KeyType> *allKeys;
@property(readonly, copy) NSArray<ObjectType> *allValues;
- (nullable ObjectType)objectForKey:(KeyType)aKey;
- (nullable ObjectType)objectForKeyedSubscript:(KeyType)key;
- (NSEnumerator *)keyEnumerator;
- (NSEnumerator *)objectEnumerator;
- (void)enumerateKeysAndObjectsUsingBlock:(void (^NS_NOESCAPE)(KeyType key, ObjectType obj, BOOL *stop))block;
+ (instancetype)dictionary;
+ (instancetype)dictionaryWithObject:(ObjectType)object forKey:(KeyType<NSCopying>)key;
+ (instancetype)dictionaryWithObjects:(const ObjectType _Nonnull[_Nonnull])objects forKeys:(const KeyType<NSCopying> _Nonnull[_Nonnull])keys count:(NSInteger)cnt;
+ (instancetype)dictionaryWithDictionary:(NSDictionary<KeyType, ObjectType> *)dict;
- (instancetype)initWithDictionary:(NSDictionary<KeyType, ObjectType> *)otherDictionary;
@end

@interface NSMutableDictionary<KeyType, ObjectType> : NSDictionary
- (instancetype)init;
- (void)setObject:(ObjectType)anObject forKey:(KeyType<NSCopying>)aKey;
- (void)setObject:(nullable ObjectType)obj forKeyedSubscript:(KeyType<NSCopying>)key;
- (void)removeObjectForKey:(KeyType)aKey;
- (void)removeAllObjects;
- (void)addEntriesFromDictionary:(NSDictionary<KeyType, ObjectType> *)otherDictionary;
+ (instancetype)dictionaryWithCapacity:(NSUInteger)numItems;
- (instancetype)initWithCapacity:(NSUInteger)numItems;
@end

@interface NSSet<__covariant ObjectType> : NSObject <NSCopying, NSMutableCopying, NSSecureCoding, NSFastEnumeration>
@property(readonly) NSInteger count;
@property(readonly, copy) NSArray *allObjects;
- (nullable ObjectType)anyObject;
- (BOOL)containsObject:(ObjectType)anObject;
+ (instancetype)set;
+ (instancetype)setWithObject:(ObjectType)object;
+ (instancetype)setWithArray:(NSArray *)array;
- (NSSet<ObjectType> *)objectsPassingTest:(BOOL (^NS_NOESCAPE)(ObjectType obj, BOOL *stop))predicate;
@end

@interface NSMutableSet<ObjectType> : NSSet<ObjectType>
- (void)addObject:(ObjectType)object;
- (void)removeObject:(ObjectType)object;
- (void)removeAllObjects;
- (NSSet<ObjectType> *)objectsPassingTest:(BOOL (^NS_NOESCAPE)(ObjectType obj, BOOL *stop))predicate;
@end

@interface NSURL : NSObject <NSSecureCoding, NSCopying>
@property(readonly, copy, nullable) NSString *scheme;
@property(readonly, copy, nullable) NSString *host;
@property(readonly, copy, nullable) NSString *path;
@property(readonly, copy, nullable) NSString *query;
@property(readonly, copy, nullable) NSString *fragment;
@property(readonly, copy, nullable) NSString *absoluteString;
@property(readonly, getter=isFileURL) BOOL fileURL;
+ (nullable instancetype)URLWithString:(NSString *)URLString;
+ (instancetype)fileURLWithPath:(NSString *)path;
- (nullable instancetype)initWithString:(NSString *)URLString;
- (nullable NSURL *)URLByAppendingPathComponent:(NSString *)pathComponent;
@end

__attribute__((swift_name("Bundle"))) @interface NSBundle : NSObject
@property(class, readonly, strong) NSBundle *mainBundle;
@property(readonly, copy) NSString *bundlePath;
@property(readonly, copy, nullable) NSString *bundleIdentifier;
@property(readonly, copy, nullable) NSDictionary *infoDictionary;
+ (nullable NSBundle *)bundleWithPath:(NSString *)path;
+ (nullable NSBundle *)bundleForClass:(Class)aClass;
+ (nullable NSBundle *)bundleWithIdentifier:(NSString *)identifier;
- (nullable NSString *)pathForResource:(nullable NSString *)name ofType:(nullable NSString *)ext;
- (nullable NSURL *)URLForResource:(nullable NSString *)name withExtension:(nullable NSString *)ext;
- (nullable id)objectForInfoDictionaryKey:(NSString *)key;
@end

@interface NSError : NSObject <NSCopying, NSSecureCoding>
@property(readonly, copy) NSErrorDomain domain;
@property(readonly) NSInteger code;
@property(readonly, copy) NSDictionary<NSErrorUserInfoKey, id> *userInfo;
@property(readonly, copy) NSString *localizedDescription;
+ (instancetype)errorWithDomain:(NSErrorDomain)domain code:(NSInteger)code userInfo:(nullable NSDictionary<NSErrorUserInfoKey, id> *)dict;
@end

@interface NSUserActivity : NSObject
@property(copy, nullable) NSString *title;
@property(copy, readonly) NSString *activityType;
@property(copy, nullable) NSURL *webpageURL;
@property(copy, nullable) NSDictionary *userInfo;
- (instancetype)initWithActivityType:(NSString *)activityType;
@end

@interface NSCoder : NSObject
@end

@interface NSNotification : NSObject
@property(readonly, copy) NSNotificationName name;
@property(readonly, strong, nullable) id object;
@property(readonly, copy, nullable) NSDictionary *userInfo;
@end

__attribute__((swift_name("NotificationCenter"))) @interface NSNotificationCenter : NSObject
@property(class, readonly, strong) NSNotificationCenter *defaultCenter;
- (void)addObserver:(id)observer selector:(SEL)aSelector name:(nullable NSNotificationName)aName object:(nullable id)anObject;
- (void)removeObserver:(id)observer;
- (void)postNotificationName:(NSNotificationName)aName object:(nullable id)anObject;
- (id <NSObject>)addObserverForName:(nullable NSNotificationName)name object:(nullable id)anObject queue:(nullable NSOperationQueue *)queue usingBlock:(void (^)(NSNotification *notification))block;
- (void)removeObserver:(id)observer name:(nullable NSNotificationName)aName object:(nullable id)anObject;
@end

@interface NSOperationQueue : NSObject
+ (NSOperationQueue *)mainQueue;
+ (nullable NSOperationQueue *)currentQueue;
@end

@interface NSUUID : NSObject <NSCopying>
+ (instancetype)UUID;
- (instancetype)initWithUUIDString:(NSString *)string;
- (instancetype)initWithUUIDBytes:(const uint8_t *)bytes;
@property(readonly, copy) NSString *UUIDString;
- (void)getUUIDBytes:(uint8_t *)uuid;
@end

/* NSError codes (NSCocoaErrorDomain file errors) the app matches on. */
enum {
    NSFileNoSuchFileError = 4,
    NSFileLockingError = 255,
    NSFileReadUnknownError = 256,
    NSFileReadNoPermissionError = 257,
    NSFileReadInvalidFileNameError = 258,
    NSFileReadCorruptFileError = 259,
    NSFileReadNoSuchFileError = 260,
    NSFileReadIncompatibleFileVersionError = 261,
    NSFileReadTooLargeError = 263,
    NSFileReadUnknownStringEncodingError = 264,
    NSFileWriteInvalidFileNameError = 513,
    NSFileWriteNoPermissionError = 513 + 1,
    NSFileWriteOutOfSpaceError = 640,
    NSFileWriteVolumeReadOnlyError = 643,
};

FOUNDATION_EXPORT NSString * const NSCocoaErrorDomain;
FOUNDATION_EXPORT NSString * const NSPOSIXErrorDomain;
FOUNDATION_EXPORT NSString * const NSURLErrorDomain;

FOUNDATION_EXPORT NSString * const NSLocalizedDescriptionKey;
FOUNDATION_EXPORT NSString * const NSLocalizedFailureReasonErrorKey;


/* tgbuild: clock ids for clock_gettime_nsec_np (values mirror _time.h). */
#undef CLOCK_UPTIME_RAW
#undef CLOCK_MONOTONIC
#undef CLOCK_MONOTONIC_RAW
static const clockid_t CLOCK_UPTIME_RAW = 8;
static const clockid_t CLOCK_MONOTONIC = 6;
static const clockid_t CLOCK_MONOTONIC_RAW = 4;

FOUNDATION_EXPORT const NSTimeInterval NSTimeIntervalSince1970;

@interface NSDate : NSObject <NSCopying, NSSecureCoding>
@property(class, readonly) NSDate *distantFuture;
@property(class, readonly) NSDate *distantPast;
+ (instancetype)date;
+ (NSTimeInterval)timeIntervalSinceReferenceDate;
- (instancetype)initWithTimeIntervalSinceReferenceDate:(NSTimeInterval)ti;
+ (instancetype)dateWithTimeIntervalSince1970:(NSTimeInterval)secs;
- (instancetype)initWithTimeIntervalSince1970:(NSTimeInterval)secs;
@property(readonly) NSTimeInterval timeIntervalSince1970;
@property(readonly) NSTimeInterval timeIntervalSinceReferenceDate;
@end

__attribute__((swift_name("ProcessInfo"))) @interface NSProcessInfo : NSObject
@property(class, readonly, strong) NSProcessInfo *processInfo;
@property(readonly, copy) NSDictionary *environment;
@property(readonly, copy) NSArray *arguments;
@property(readonly) NSOperatingSystemVersion operatingSystemVersion;
@property(readonly) NSTimeInterval systemUptime;
@end

__attribute__((swift_name("UserDefaults"))) @interface NSUserDefaults : NSObject
@property(class, readonly, strong) NSUserDefaults *standardUserDefaults;
- (nullable id)objectForKey:(NSString *)defaultName;
- (void)setObject:(nullable id)value forKey:(NSString *)defaultName __attribute__((swift_name("set(_:forKey:)")));
- (BOOL)boolForKey:(NSString *)defaultName;
- (void)setBool:(BOOL)value forKey:(NSString *)defaultName __attribute__((swift_name("set(_:forKey:)")));
@end

@interface NSNull : NSObject <NSCopying, NSSecureCoding>
+ (NSNull *)null;
@end

typedef NS_ENUM(NSUInteger, NSSearchPathDirectory) { NSDocumentDirectory = 9, NSCachesDirectory = 13, NSApplicationSupportDirectory = 14, NSLibraryDirectory = 5 };
typedef NS_OPTIONS(NSUInteger, NSSearchPathDomainMask) { NSUserDomainMask = 1, NSLocalDomainMask = 2, NSAllDomainsMask = 0x0ffff };
typedef NSString *NSFileAttributeKey __attribute__((swift_wrapper(struct)));
typedef NSString *NSFileProtectionType __attribute__((swift_wrapper(struct)));
FOUNDATION_EXPORT NSFileAttributeKey const NSFileProtectionKey;
FOUNDATION_EXPORT NSErrorDomain const NSCocoaErrorDomain;
FOUNDATION_EXPORT NSFileProtectionType const NSFileProtectionNone;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSLocalizedDescriptionKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSUnderlyingErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSLocalizedFailureReasonErrorKey;
FOUNDATION_EXPORT NSArray *NSSearchPathForDirectoriesInDomains(NSSearchPathDirectory directory, NSSearchPathDomainMask domainMask, BOOL expandTilde);
FOUNDATION_EXPORT NSString *NSTemporaryDirectory(void);

@class NSDirectoryEnumerator;

@interface NSIndexSet : NSObject <NSCopying, NSMutableCopying, NSSecureCoding>
@property (readonly) NSUInteger count;
@property (readonly) NSUInteger firstIndex;
@property (readonly) NSUInteger lastIndex;
- (instancetype)initWithIndex:(NSUInteger)value;
- (nullable instancetype)initWithIndexSet:(NSIndexSet *)indexSet;
- (instancetype)initWithIndexes:(const NSUInteger *)indexes count:(NSUInteger)cnt;
- (instancetype)initWithRange:(NSRange)range;
- (BOOL)containsIndex:(NSUInteger)value;
- (BOOL)containsIndexes:(NSIndexSet *)indexSet;
- (BOOL)containsIndexesInRange:(NSRange)range;
- (BOOL)intersectsIndexesInRange:(NSRange)range;
- (NSUInteger)countOfIndexesInRange:(NSRange)range;
- (NSUInteger)indexGreaterThanIndex:(NSUInteger)value;
- (NSUInteger)indexLessThanIndex:(NSUInteger)value;
- (NSUInteger)indexLessThanOrEqualToIndex:(NSUInteger)value;
- (NSUInteger)indexGreaterThanOrEqualToIndex:(NSUInteger)value;
- (NSUInteger)indexLessThanOrEqualToIndex:(NSUInteger)value;
- (void)getIndexes:(NSUInteger *)indexBuffer maxCount:(NSUInteger)maxCount inIndexRange:(nullable NSRange *)range;
- (void)enumerateRangesUsingBlock:(void (^)(NSRange range, BOOL *stop))block;
- (void)enumerateRangesWithOptions:(NSUInteger)opts usingBlock:(void (^)(NSRange range, BOOL *stop))block;
- (void)enumerateIndexesUsingBlock:(void (^)(NSUInteger idx, BOOL *stop))block;
- (void)enumerateIndexesWithOptions:(NSUInteger)opts usingBlock:(void (^)(NSUInteger idx, BOOL *stop))block;
@end

@interface NSMutableIndexSet : NSIndexSet <NSCopying, NSMutableCopying>
+ (instancetype)indexSet;
+ (instancetype)indexSetWithIndex:(NSUInteger)value;
+ (instancetype)indexSetWithIndexesInRange:(NSRange)range;
- (void)addIndexes:(NSIndexSet *)indexes;
- (void)removeIndexes:(NSIndexSet *)indexes;
- (void)addIndex:(NSUInteger)value;
- (void)removeIndex:(NSUInteger)value;
- (void)removeAllIndexes;
- (void)addIndexesInRange:(NSRange)range;
- (void)removeIndexesInRange:(NSRange)range;
- (void)shiftIndexesStartingAtIndex:(NSUInteger)index by:(NSInteger)delta;
@end

/* tgbuild: NS_ROOT_CLASS (objc_root_class marker; real SDK defines it in NSObject.h). */
#ifndef NS_ROOT_CLASS
#define NS_ROOT_CLASS __attribute__((objc_root_class))
#endif

/* URL loading: the subset the app's WebKit carrier and networking code use.
   Enums whose names begin with a class name nest under it in Swift
   (NSURLSessionAuthChallengeDisposition -> URLSession.AuthChallengeDisposition). */
typedef NS_ENUM(NSUInteger, NSURLRequestCachePolicy) {
    NSURLRequestUseProtocolCachePolicy = 0,
    NSURLRequestReloadIgnoringLocalCacheData = 1,
    NSURLRequestReloadIgnoringLocalAndRemoteCacheData = 4,
    NSURLRequestReturnCacheDataElseLoad = 2,
    NSURLRequestReloadRevalidatingCacheData = 5,
};

typedef NS_ENUM(NSInteger, NSURLSessionAuthChallengeDisposition) {
    NSURLSessionAuthChallengeUseCredential = 0,
    NSURLSessionAuthChallengePerformDefaultHandling = 1,
    NSURLSessionAuthChallengeCancelAuthenticationChallenge = 2,
    NSURLSessionAuthChallengeRejectProtectionSpace = 3,
} __attribute__((swift_name("URLSession.AuthChallengeDisposition")));

FOUNDATION_EXPORT NSString * const NSURLAuthenticationMethodServerTrust;

__attribute__((swift_name("URLRequest"))) @interface NSURLRequest : NSObject <NSSecureCoding, NSCopying>
+ (instancetype)requestWithURL:(NSURL *)URL;
- (instancetype)initWithURL:(NSURL *)URL;
- (instancetype)initWithURL:(NSURL *)URL cachePolicy:(NSURLRequestCachePolicy)cachePolicy timeoutInterval:(NSTimeInterval)timeoutInterval;
@property (nullable, readonly, copy) NSURL *URL;
@property (readonly) NSURLRequestCachePolicy cachePolicy;
@property (readonly) NSTimeInterval timeoutInterval;
@end

@interface NSMutableURLRequest : NSURLRequest
@property (nullable, copy) NSURL *URL;
@end

__attribute__((swift_name("URLResponse"))) @interface NSURLResponse : NSObject <NSSecureCoding, NSCopying>
@property (nullable, readonly, copy) NSURL *URL;
@property (nullable, readonly, copy) NSString *MIMEType;
@property (readonly) long long expectedContentLength;
@property (nullable, readonly, copy) NSString *textEncodingName;
@end

__attribute__((swift_name("HTTPURLResponse"))) @interface NSHTTPURLResponse : NSURLResponse
@property (readonly) NSInteger statusCode;
@end

@interface NSHTTPURLResponse (TgbuildAdditions)
+ (nullable instancetype)localizedStringForStatusCode:(NSInteger)statusCode;
@end

__attribute__((swift_name("URLQueryItem"))) @interface NSURLQueryItem : NSObject <NSSecureCoding, NSCopying>
+ (instancetype)queryItemWithName:(NSString *)name value:(nullable NSString *)value;
@property (readonly, copy) NSString *name;
@property (nullable, readonly, copy) NSString *value;
@end

@interface NSKeyedArchiver : NSObject
+ (NSData *)tg_archivedDataWithRootObject:(id)obj requiringSecureCoding:(BOOL)requiresSecureCoding error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("__archivedData(withRootObject:requiringSecureCoding:error:)")));
@end

@interface NSKeyedUnarchiver : NSObject
+ (nullable id)unarchivedObjectOfClass:(Class)cls fromData:(NSData *)data error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("unarchivedObject(ofClass:from:)")));
+ (nullable id)unarchiveTopLevelObjectWithData:(NSData *)data error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("unarchiveTopLevelObjectWithData(_)")));
@end

typedef NS_ENUM(NSUInteger, NSRoundingMode) {
    NSRoundPlain __attribute__((swift_name("plain"))),
    NSRoundDown __attribute__((swift_name("down"))),
    NSRoundUp __attribute__((swift_name("up"))),
    NSRoundBankers __attribute__((swift_name("bankers"))),
};

@protocol NSDecimalNumberBehaviors <NSObject>
- (NSRoundingMode)roundingMode;
- (short)scale;
@end

@interface NSDecimalNumber : NSNumber
- (instancetype)initWithDouble:(double)v;
- (instancetype)initWithInt:(int)v;
- (instancetype)initWithLongLong:(long long)v;
- (instancetype)initWithBool:(BOOL)v;
- (NSDecimalNumber *)roundingAccordingToBehavior:(id <NSDecimalNumberBehaviors>)behavior;
@end

@interface NSDecimalNumberHandler : NSObject <NSDecimalNumberBehaviors>
+ (NSDecimalNumberHandler *)decimalNumberHandlerWithRoundingMode:(NSRoundingMode)roundingMode scale:(short)scale raiseOnExactness:(BOOL)raiseOnExactness raiseOnOverflow:(BOOL)raiseOnOverflow raiseOnUnderflow:(BOOL)raiseOnUnderflow raiseOnDivideByZero:(BOOL)raiseOnDivideByZero;
@end

typedef NS_OPTIONS(NSUInteger, NSRegularExpressionOptions) {
    NSRegularExpressionCaseInsensitive = 1 << 0,
    NSRegularExpressionAllowCommentsAndWhitespace = 1 << 1,
    NSRegularExpressionAnchorsMatchLines = 1 << 3,
    NSRegularExpressionUseUnicodeWordBoundaries = 1 << 6,
} __attribute__((swift_name("NSRegularExpression.Options")));

typedef NS_OPTIONS(NSUInteger, NSMatchingOptions) {
    NSMatchingReportProgress = 1 << 0,
    NSMatchingReportCompletion = 1 << 1,
    NSMatchingAnchored = 1 << 2,
    NSMatchingWithTransparentBounds = 1 << 3,
    NSMatchingWithoutTransparentBounds = 1 << 4,
} __attribute__((swift_name("NSRegularExpression.MatchingOptions")));

typedef NS_OPTIONS(NSUInteger, NSMatchingFlags) {
    NSMatchingProgress = 1 << 0,
    NSMatchingCompleted = 1 << 1,
    NSMatchingHitEnd = 1 << 2,
    NSMatchingRequiredEnd = 1 << 3,
    NSMatchingTerminated = 1 << 4,
} __attribute__((swift_name("NSRegularExpression.MatchingFlags")));

@interface NSTextCheckingResult : NSObject
@property (readonly) NSRange range;
@end

@interface NSRegularExpression : NSObject <NSCopying, NSSecureCoding>
+ (nullable NSRegularExpression *)regularExpressionWithPattern:(NSString *)pattern options:(NSRegularExpressionOptions)options error:(NSError * _Nullable * _Nullable)error;
- (nullable instancetype)initWithPattern:(NSString *)pattern options:(NSRegularExpressionOptions)options error:(NSError * _Nullable * _Nullable)error;
@property (readonly, copy) NSString *pattern;
- (nullable NSArray *)matchesInString:(NSString *)string options:(NSMatchingOptions)options range:(NSRange)range;
- (nullable NSTextCheckingResult *)firstMatchInString:(NSString *)string options:(NSMatchingOptions)options range:(NSRange)range;
- (NSUInteger)numberOfMatchesInString:(NSString *)string options:(NSMatchingOptions)options range:(NSRange)range;
- (NSString *)stringByReplacingMatchesInString:(NSString *)string options:(NSMatchingOptions)options range:(NSRange)range withTemplate:(NSString *)templ;
@end

FOUNDATION_EXPORT NSString * const NSUbiquitousKeyValueStoreDidChangeExternallyNotification;

@interface NSUbiquitousKeyValueStore : NSObject
@property(class, readonly, strong) NSUbiquitousKeyValueStore *defaultStore __attribute__((swift_name("default")));
- (nullable id)objectForKey:(NSString *)key;
- (void)setObject:(nullable id)value forKey:(NSString *)key __attribute__((swift_name("set(_:forKey:)")));
- (void)setString:(nullable NSString *)value forKey:(NSString *)key;
- (void)removeObjectForKey:(NSString *)key;
- (BOOL)synchronize;
@end

typedef NS_OPTIONS(NSUInteger, NSJSONReadingOptions) {
    NSJSONReadingMutableContainers = (1UL << 0),
    NSJSONReadingMutableLeaves = (1UL << 1),
    NSJSONReadingFragmentsAllowed = (1UL << 22),
    NSJSONReadingJSON5Allowed = (1UL << 23),
} __attribute__((swift_name("JSONSerialization.ReadingOptions")));

typedef NS_OPTIONS(NSUInteger, NSJSONWritingOptions) {
    NSJSONWritingPrettyPrinted = (1UL << 0),
    NSJSONWritingSortedKeys = (1UL << 1),
    NSJSONWritingFragmentsAllowed = (1UL << 23),
    NSJSONWritingWithoutEscapingSlashes = (1UL << 24),
} __attribute__((swift_name("JSONSerialization.WritingOptions")));

__attribute__((swift_name("JSONSerialization"))) @interface NSJSONSerialization : NSObject
+ (BOOL)isValidJSONObject:(id)obj;
+ (nullable NSData *)dataWithJSONObject:(id)obj options:(NSJSONWritingOptions)opt error:(NSError * _Nullable * _Nullable)error;
+ (nullable id)JSONObjectWithData:(NSData *)data options:(NSJSONReadingOptions)opt error:(NSError * _Nullable * _Nullable)error;
+ (nullable id)JSONObjectWithData:(NSData *)data error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("jsonObject(with:)")));
+ (nullable NSData *)dataWithJSONObject:(id)obj options:(NSJSONWritingOptions)opt error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("data(withJSONObject:options:)")));
+ (nullable NSData *)dataWithJSONObject:(id)obj error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("data(withJSONObject:)")));
@end

__attribute__((swift_name("URLComponents"))) @interface NSURLComponents : NSObject <NSSecureCoding>
- (instancetype)init;
- (nullable instancetype)initWithURL:(NSURL *)URL resolvingAgainstBaseURL:(BOOL)resolve;
- (nullable instancetype)initWithString:(NSString *)URLString;
@property (nullable, copy) NSString *scheme;
@property (nullable, copy) NSString *user;
@property (nullable, copy) NSString *password;
@property (nullable, copy) NSString *host;
@property (nullable, copy) NSString *portNumber;
@property (nullable, copy) NSNumber *tg_portNumberValue;
@property (nullable, readonly) NSNumber *portNumberValue;

@property (copy) NSString *path;
@property (nullable, copy) NSString *query;
@property (nullable, copy) NSString *fragment;
@property (nullable, copy) NSArray<NSURLQueryItem *> *queryItems;
@property (nullable, copy) NSArray<NSURLQueryItem *> *percentEncodedQueryItems;
@property (nullable, readonly, copy) NSString *string;
@property (nullable, readonly, copy) NSURL *URL;
@property (nullable, copy) NSString *percentEncodedPath;
@end

__attribute__((swift_name("URLSession"))) @interface NSURLSession : NSObject
@end
__attribute__((swift_name("URLCredential"))) @interface NSURLCredential : NSObject <NSSecureCoding, NSCopying>
@end

__attribute__((swift_name("URLProtectionSpace"))) @interface NSURLProtectionSpace : NSObject <NSSecureCoding, NSCopying>
@property (readonly, copy) NSString *authenticationMethod;
@end

__attribute__((swift_name("URLAuthenticationChallenge"))) @interface NSURLAuthenticationChallenge : NSObject
@property (readonly, strong) NSURLProtectionSpace *protectionSpace;
@end

__attribute__((swift_name("FileManager"))) @interface NSFileManager : NSObject
@property(class, readonly, strong) NSFileManager *defaultManager;
- (BOOL)fileExistsAtPath:(NSString *)path;
- (BOOL)fileExistsAtPath:(NSString *)path isDirectory:(nullable BOOL *)isDirectory;
- (BOOL)createDirectoryAtPath:(NSString *)path withIntermediateDirectories:(BOOL)createIntermediates attributes:(nullable NSDictionary *)attributes error:(NSError * _Nullable * _Nullable)error;
- (BOOL)removeItemAtPath:(NSString *)path error:(NSError * _Nullable * _Nullable)error;
- (BOOL)copyItemAtPath:(NSString *)srcPath toPath:(NSString *)dstPath error:(NSError * _Nullable * _Nullable)error;
- (nullable NSArray *)contentsOfDirectoryAtPath:(NSString *)path error:(NSError * _Nullable * _Nullable)error;
- (BOOL)moveItemAtPath:(NSString *)srcPath toPath:(NSString *)dstPath error:(NSError * _Nullable * _Nullable)error;
- (BOOL)linkItemAtPath:(NSString *)srcPath toPath:(NSString *)dstPath error:(NSError * _Nullable * _Nullable)error;
- (nullable NSDirectoryEnumerator *)enumeratorAtPath:(NSString *)path;
- (nullable NSDictionary *)attributesOfItemAtPath:(NSString *)path error:(NSError * _Nullable * _Nullable)error;
@end

__attribute__((swift_name("FileManager.DirectoryEnumerator"))) @interface NSDirectoryEnumerator : NSObject
- (nullable id)nextObject;
@end

@interface NSString (NSStringPathExtensions)
@property(readonly, copy) NSString *lastPathComponent;
@property(readonly, copy) NSString *pathExtension;
@property(readonly, copy) NSString *stringByDeletingLastPathComponent;
@property(readonly, copy) NSString *stringByDeletingPathExtension;
- (NSString *)stringByAppendingPathComponent:(NSString *)str;
@end

@interface NSLocale : NSObject <NSCopying, NSSecureCoding>
+ (NSLocale *)localeWithLocaleIdentifier:(NSString *)string;
- (instancetype)initWithLocaleIdentifier:(NSString *)string;
@property(class, readonly, copy) NSLocale *currentLocale;
@end
@interface NSTimeZone : NSObject <NSCopying, NSSecureCoding>
+ (nullable NSTimeZone *)timeZoneForSecondsFromGMT:(NSInteger)seconds;
+ (nullable NSTimeZone *)timeZoneWithName:(NSString *)tzName;
@property(class, readonly, copy) NSTimeZone *localTimeZone;
@end
@interface NSCharacterSet : NSObject <NSCopying, NSSecureCoding>
@property(class, readonly, strong) NSCharacterSet *whitespaceCharacterSet;
@property(class, readonly, strong) NSCharacterSet *whitespaceAndNewlineCharacterSet;
@property(class, readonly, strong) NSCharacterSet *alphanumericCharacterSet;
@property(class, readonly, strong) NSCharacterSet *decimalDigitCharacterSet;
@property(class, readonly, strong) NSCharacterSet *letterCharacterSet;
@property(class, readonly, strong) NSCharacterSet *newlineCharacterSet;
- (instancetype)initWithCharactersInString:(NSString *)string;
- (BOOL)characterIsMember:(unichar)member;
- (nullable NSCharacterSet *)invertedSet;
@end
@interface NSLock : NSObject
- (instancetype)init;
- (void)lock;
- (void)unlock;
- (BOOL)tryLock;
- (BOOL)lockBeforeDate:(NSDate *)limit;
@end

@interface NSRecursiveLock : NSObject
- (instancetype)init;
- (void)lock;
- (void)unlock;
- (BOOL)tryLock;
@property(readonly) BOOL inLazySetupMode;
@end

typedef struct CF_BRIDGED_TYPE(id) __CFStringTokenizer *CFStringTokenizerRef;
enum {
    kCFStringTokenizerUnitWord = 1,
    kCFStringTokenizerUnitSentence = 2,
    kCFStringTokenizerUnitParagraph = 3,
    kCFStringTokenizerUnitLineBreak = 4
};
typedef CF_OPTIONS(CFIndex, CFStringTokenizerTokenType) {
    kCFStringTokenizerTokenNormal = (1 << 0),
    kCFStringTokenizerTokenHasSubTokensMask = (1 << 1),
    kCFStringTokenizerTokenHasDerivedSubTokensMask = (1 << 2),
    kCFStringTokenizerTokenHasHasNumbersMask = (1 << 3),
    kCFStringTokenizerTokenHasNonLettersMask = (1 << 4),
    kCFStringTokenizerTokenIsCJWordMask = (1 << 5)
};
CF_RETURNS_RETAINED CFStringTokenizerRef CFStringTokenizerCreate(CFAllocatorRef alloc, CFStringRef string, CFRange range, CFOptionFlags options, CFLocaleRef locale);
CFStringTokenizerTokenType CFStringTokenizerAdvanceToNextToken(CFStringTokenizerRef tokenizer);
CFRange CFStringTokenizerGetCurrentTokenRange(CFStringTokenizerRef tokenizer);

__attribute__((swift_name("DateFormatter"))) @interface NSDateFormatter : NSObject
@property(nullable, copy) NSString *dateFormat;
@property(nullable, copy) NSLocale *locale;
@property(nullable, copy) NSTimeZone *timeZone;
- (NSString *)stringFromDate:(NSDate *)date;
- (nullable NSDate *)dateFromString:(NSString *)string;
@end

typedef NS_OPTIONS(NSUInteger, NSKeyValueObservingOptions) { NSKeyValueObservingOptionNew = 1, NSKeyValueObservingOptionOld = 2, NSKeyValueObservingOptionInitial = 4, NSKeyValueObservingOptionPrior = 8 };
typedef NSString *NSKeyValueChangeKey __attribute__((swift_wrapper(struct)));
typedef NS_ENUM(NSUInteger, NSStreamStatus) {
  NSStreamStatusNotOpen = 0, NSStreamStatusOpening = 1, NSStreamStatusOpen = 2, NSStreamStatusReading = 3,
  NSStreamStatusWriting = 4, NSStreamStatusAtEnd = 5, NSStreamStatusClosed = 6, NSStreamStatusError = 7
};
typedef NS_OPTIONS(NSUInteger, NSStreamEvent) {
  NSStreamEventNone = 0, NSStreamEventOpenCompleted = 1 << 0, NSStreamEventHasBytesAvailable = 1 << 1,
  NSStreamEventHasSpaceAvailable = 1 << 2, NSStreamEventErrorOccurred = 1 << 3, NSStreamEventEndEncountered = 1 << 4
};
typedef NSString *NSStreamPropertyKey __attribute__((swift_wrapper(struct)));
@class NSStream;
@protocol NSStreamDelegate <NSObject>
@optional
- (void)stream:(NSStream *)aStream handleEvent:(NSStreamEvent)eventCode;
@end
__attribute__((swift_name("Stream"))) @interface NSStream : NSObject
@property(nullable, assign) id<NSStreamDelegate> delegate;
@property(readonly) NSStreamStatus streamStatus;
@property(nullable, readonly, copy) NSError *streamError;
- (void)open;
- (void)close;
- (void)scheduleInRunLoop:(NSRunLoop *)aRunLoop forMode:(NSRunLoopMode)mode;
- (void)removeFromRunLoop:(NSRunLoop *)aRunLoop forMode:(NSRunLoopMode)mode;
- (nullable id)propertyForKey:(NSStreamPropertyKey)key;
@end
__attribute__((swift_name("OutputStream"))) @interface NSOutputStream : NSStream
+ (nullable instancetype)outputStreamToMemory;
- (nullable instancetype)initToMemory;
- (NSInteger)write:(const uint8_t *)buffer maxLength:(NSUInteger)len;
- (BOOL)hasSpaceAvailable;
@end

__attribute__((swift_name("InputStream"))) @interface NSInputStream : NSStream
- (NSInteger)read:(uint8_t *)buffer maxLength:(NSUInteger)len;
@property(readonly) BOOL hasBytesAvailable;
- (instancetype)initWithData:(NSData *)data;
@end
@interface NSObject (TgbuildPerform)
- (void)performSelector:(SEL)aSelector onThread:(NSThread *)thread withObject:(nullable id)arg waitUntilDone:(BOOL)wait;
@end

__attribute__((swift_name("RunLoop"))) @interface NSRunLoop : NSObject
@property(class, readonly, strong) NSRunLoop *currentRunLoop;
@property(class, readonly, strong) NSRunLoop *mainRunLoop;
- (void)run;
- (void)runUntilDate:(NSDate *)limitDate;
@end
@interface NSCondition : NSObject
- (void)lock;
- (void)unlock;
- (void)wait;
- (void)signal;
- (void)broadcast;
@end
@interface NSMethodSignature : NSObject
+ (nullable NSMethodSignature *)signatureWithObjCTypes:(const char *)types;
@property(readonly) NSUInteger numberOfArguments;
@property(readonly) const char *methodReturnType NS_RETURNS_INNER_POINTER;
- (const char *)getArgumentTypeAtIndex:(NSUInteger)idx NS_RETURNS_INNER_POINTER;
@end
typedef NS_ENUM(NSInteger, NSItemProviderRepresentationVisibility) {
  NSItemProviderRepresentationVisibilityAll = 0, NSItemProviderRepresentationVisibilityTeam = 1,
  NSItemProviderRepresentationVisibilityGroup = 2, NSItemProviderRepresentationVisibilityOwnProcess = 3
};
@interface NSObject (NSKeyValueObserving)
- (void)observeValueForKeyPath:(nullable NSString *)keyPath ofObject:(nullable id)object change:(nullable NSDictionary *)change context:(nullable void *)context;
- (void)addObserver:(NSObject *)observer forKeyPath:(NSString *)keyPath options:(NSKeyValueObservingOptions)options context:(nullable void *)context;
- (void)removeObserver:(NSObject *)observer forKeyPath:(NSString *)keyPath;
@end
@protocol NSItemProviderReading <NSObject>
@end
@protocol NSItemProviderWriting <NSObject>
@end
@protocol NSPortDelegate <NSObject>
@end
@interface NSObject (NSKeyValueObservingContext)
- (void)removeObserver:(NSObject *)observer forKeyPath:(NSString *)keyPath context:(nullable void *)context;
@end
__attribute__((swift_name("Thread"))) @interface NSThread : NSObject
@property(class, readonly) BOOL isMainThread;
@end

NS_ASSUME_NONNULL_END

#include <dispatch/dispatch.h>
#include <utime.h>
/* tgbuild: non-variadic fcntl helpers; the variadic fcntl imports as unavailable in Swift
   and the app calls it with pointer/int third args that a single signature cannot cover. */
static inline int _tg_fcntl2(int fd, int cmd) { return fcntl(fd, cmd); }
static inline int _tg_fcntl3(int fd, int cmd, int arg) { return fcntl(fd, cmd, arg); }
static inline int _tg_fcntl3p(int fd, int cmd, void *arg) { return fcntl(fd, cmd, arg); }
// Declarations added for the Swift Foundation overlay build (authored from public API behaviour; not Apple's file).
// Appended to the module-clean copy of Foundation.h by mk-sdkm2.sh.
/* NSInteger for size/count members: the 6.x importer maps NSUInteger to UInt while the
   5.3 overlay sources pass Int; same ABI. */
#pragma once
NS_ASSUME_NONNULL_BEGIN
@interface NSDictionary (W71OverlayAdditions)
- (void)getObjects:(id _Nonnull __unsafe_unretained * _Nullable)objects andKeys:(id _Nonnull __unsafe_unretained * _Nullable)keys count:(NSUInteger)count;
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
@interface NSBundle (W71OverlayAdditions)
- (NSString *)localizedStringForKey:(NSString *)key value:(nullable NSString *)value table:(nullable NSString *)tableName;
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
@interface NSUserDefaults (W71OverlayAdditions)
- (nullable instancetype)initWithSuiteName:(nullable NSString *)suitename;
+ (void)resetStandardUserDefaults;
- (void)removeObjectForKey:(NSString *)defaultName;
- (nullable NSString *)stringForKey:(NSString *)defaultName;
- (nullable NSArray *)arrayForKey:(NSString *)defaultName;
- (nullable NSDictionary *)dictionaryForKey:(NSString *)defaultName;
- (nullable NSArray *)stringArrayForKey:(NSString *)defaultName;
- (NSInteger)integerForKey:(NSString *)defaultName;
- (float)floatForKey:(NSString *)defaultName;
- (double)doubleForKey:(NSString *)defaultName;
- (void)setInteger:(NSInteger)value forKey:(NSString *)defaultName __attribute__((swift_name("set(_:forKey:)")));
- (void)setFloat:(float)value forKey:(NSString *)defaultName __attribute__((swift_name("set(_:forKey:)")));
- (void)setDouble:(double)value forKey:(NSString *)defaultName __attribute__((swift_name("set(_:forKey:)")));
- (void)registerDefaults:(NSDictionary *)registrationDictionary;
- (NSDictionary *)dictionaryRepresentation;
- (nullable NSDictionary *)persistentDomainForName:(NSString *)domainName;
- (void)setPersistentDomain:(NSDictionary *)domain forName:(NSString *)domainName;
- (void)removePersistentDomainForName:(NSString *)domainName;
- (BOOL)synchronize;
@end
@interface NSThread (W71OverlayAdditions)
@property(class, readonly, copy) NSArray *callStackSymbols;
@property(class, readonly, strong) NSThread *currentThread;
@property(class, readonly, strong) NSThread *mainThread;
+ (void)sleepForTimeInterval:(NSTimeInterval)ti;
- (instancetype)initWithTarget:(id)target selector:(SEL)selector object:(nullable id)argument;
@property double threadPriority;
- (void)start;
@property (readonly) BOOL isExecuting;
@property (readonly) BOOL isFinished;
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT NSInteger NSPageSize(void);
typedef NS_OPTIONS(NSUInteger, NSDataReadingOptions) {
  NSDataReadingMappedIfSafe __attribute__((swift_name("mappedIfSafe"))) = 1UL << 0, NSDataReadingUncached __attribute__((swift_name("uncached"))) = 1UL << 1, NSDataReadingMappedAlways __attribute__((swift_name("alwaysMapped"))) = 1UL << 3,
  NSDataReadingMapped __attribute__((swift_name("mapped"))) = NSDataReadingMappedIfSafe, NSDataReadingMappedRead __attribute__((swift_name("mappedRead"))) = 1UL << 2
};
typedef NS_OPTIONS(NSUInteger, NSDataWritingOptions) {
  NSDataWritingAtomic = 1UL << 0, NSDataWritingWithoutOverwriting = 1UL << 1,
  NSDataWritingFileProtectionNone = 0x10000000, NSDataWritingFileProtectionComplete = 0x20000000,
  NSDataWritingFileProtectionCompleteUnlessOpen = 0x30000000, NSDataWritingFileProtectionCompleteUntilFirstUserAuthentication = 0x40000000,
  NSDataWritingFileProtectionMask = 0xf0000000
};
typedef NS_OPTIONS(NSUInteger, NSDataSearchOptions) { NSDataSearchBackwards = 1UL << 0, NSDataSearchAnchored = 1UL << 1 }
;
typedef NS_OPTIONS(NSUInteger, NSDataBase64EncodingOptions) {
  NSDataBase64Encoding64CharacterLineLength = 1UL << 0, NSDataBase64Encoding76CharacterLineLength = 1UL << 1,
  NSDataBase64EncodingEndLineWithCarriageReturn = 1UL << 4, NSDataBase64EncodingEndLineWithLineFeed = 1UL << 5
} __attribute__((swift_name("NSData.Base64EncodingOptions")));
typedef NS_OPTIONS(NSUInteger, NSDataBase64DecodingOptions) { NSDataBase64DecodingIgnoreUnknownCharacters = 1UL << 0 }
  __attribute__((swift_name("NSData.Base64DecodingOptions")));
@interface NSData (W71OverlayAdditions)
- (instancetype)initWithBytesNoCopy:(void *)bytes length:(NSInteger)length deallocator:(nullable void (^)(void *bytes, NSInteger length))deallocator;
- (instancetype)initWithBytesNoCopy:(void *)bytes length:(NSInteger)length freeWhenDone:(BOOL)b;
- (instancetype)initWithBytesNoCopy:(void *)bytes length:(NSInteger)length;
- (instancetype)initWithData:(NSData *)data;
- (nullable instancetype)initWithContentsOfFile:(NSString *)path options:(NSDataReadingOptions)readOptionsMask error:(NSError **)errorPtr;
- (nullable instancetype)initWithContentsOfURL:(NSURL *)url options:(NSDataReadingOptions)readOptionsMask error:(NSError **)errorPtr;
- (nullable instancetype)initWithBase64EncodedString:(NSString *)base64String options:(NSDataBase64DecodingOptions)options __attribute__((swift_name("init(base64Encoded:options:)")));
- (nullable instancetype)initWithBase64EncodedData:(NSData *)base64Data options:(NSDataBase64DecodingOptions)options __attribute__((swift_name("init(base64Encoded:options:)")));
- (NSString *)base64EncodedStringWithOptions:(NSDataBase64EncodingOptions)options;
- (NSData *)base64EncodedDataWithOptions:(NSDataBase64EncodingOptions)options;
- (void)getBytes:(void *)buffer;
- (NSRange)rangeOfData:(NSData *)dataToFind options:(NSDataSearchOptions)mask range:(NSRange)searchRange __attribute__((swift_name("range(of:options:in:)")));
- (void)enumerateByteRangesUsingBlock:(void (NS_NOESCAPE ^)(const void *bytes, NSRange byteRange, BOOL *stop))block __attribute__((swift_name("enumerateBytes(_:)")));
- (BOOL)writeToFile:(NSString *)path options:(NSDataWritingOptions)writeOptionsMask error:(NSError * _Nullable * _Nullable)errorPtr;
- (BOOL)writeToURL:(NSURL *)url options:(NSDataWritingOptions)writeOptionsMask error:(NSError **)errorPtr;
- (BOOL)_isCompact;
@end
@interface NSMutableData (W71OverlayAdditions)
- (void)setLength:(NSInteger)length;
- (void)increaseLengthBy:(NSInteger)extraLength;
- (void)resetBytesInRange:(NSRange)range;
- (void)setData:(NSData *)data;
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT NSErrorUserInfoKey const NSFilePathErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSURLErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSStringEncodingErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSHelpAnchorErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSLocalizedRecoverySuggestionErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSLocalizedRecoveryOptionsErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSRecoveryAttempterErrorKey;
FOUNDATION_EXPORT NSErrorUserInfoKey const NSDebugDescriptionErrorKey;
FOUNDATION_EXPORT NSErrorDomain const NSPOSIXErrorDomain;
FOUNDATION_EXPORT NSErrorDomain const NSOSStatusErrorDomain;
FOUNDATION_EXPORT NSErrorDomain const NSMachErrorDomain;
FOUNDATION_EXPORT NSErrorDomain const NSURLErrorDomain;
typedef NS_OPTIONS(NSUInteger, NSStringEnumerationOptions) {
  NSStringEnumerationByLines = 0, NSStringEnumerationByParagraphs = 1, NSStringEnumerationByComposedCharacterSequences = 2,
  NSStringEnumerationByWords = 3, NSStringEnumerationBySentences = 4, NSStringEnumerationReverse = 1UL << 8,
  NSStringEnumerationSubstringNotRequired = 1UL << 9, NSStringEnumerationLocalized = 1UL << 10
};
typedef NS_OPTIONS(NSUInteger, NSStringEncodingConversionOptions) {
  NSStringEncodingConversionAllowLossy = 1, NSStringEncodingConversionExternalRepresentation = 2
};
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
typedef NS_OPTIONS(NSUInteger, NSURLBookmarkCreationOptions) {
  NSURLBookmarkCreationPreferFileIDResolution = 1UL << 8, NSURLBookmarkCreationMinimalBookmark = 1UL << 9,
  NSURLBookmarkCreationSuitableForBookmarkFile = 1UL << 10, NSURLBookmarkCreationWithSecurityScope = 1UL << 11,
  NSURLBookmarkCreationSecurityScopeAllowOnlyReadAccess = 1UL << 12, NSURLBookmarkCreationWithoutImplicitSecurityScope = 1UL << 29
};
typedef NS_OPTIONS(NSUInteger, NSURLBookmarkResolutionOptions) {
  NSURLBookmarkResolutionWithoutUI = 1UL << 8, NSURLBookmarkResolutionWithoutMounting = 1UL << 9,
  NSURLBookmarkResolutionWithSecurityScope = 1UL << 10, NSURLBookmarkResolutionWithoutImplicitStartAccessing = 1UL << 15
};
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT NSInteger NSRoundUpToMultipleOfPageSize(NSInteger bytes);
FOUNDATION_EXPORT NSInteger NSRoundDownToMultipleOfPageSize(NSInteger bytes);
FOUNDATION_EXPORT void NSCopyMemoryPages(const void *source, void *dest, NSInteger bytes);
FOUNDATION_EXPORT void (^const NSDataDeallocatorVM)(void *bytes, NSUInteger length);
FOUNDATION_EXPORT void (^const NSDataDeallocatorUnmap)(void *bytes, NSUInteger length);
FOUNDATION_EXPORT void (^const NSDataDeallocatorFree)(void *bytes, NSUInteger length);
FOUNDATION_EXPORT void (^const NSDataDeallocatorNone)(void *bytes, NSUInteger length);
FOUNDATION_EXPORT double NSFoundationVersionNumber;
#define NSFoundationVersionNumber_iOS_9_x_Max 1299
NS_ASSUME_NONNULL_END

typedef struct _NSZone NSZone;
NS_ASSUME_NONNULL_BEGIN
@interface NSError (W71OverlayAdditions)
+ (void)setUserInfoValueProviderForDomain:(NSErrorDomain)errorDomain provider:(nullable id _Nullable (^)(NSError *err, NSErrorUserInfoKey userInfoKey))provider __attribute__((swift_name("setUserInfoValueProvider(forDomain:provider:)")));
+ (nullable id _Nullable (^)(NSError *err, NSErrorUserInfoKey userInfoKey))userInfoValueProviderForDomain:(NSErrorDomain)errorDomain __attribute__((swift_name("userInfoValueProvider(forDomain:)")));
@end
FOUNDATION_EXPORT NSString *const NSURLErrorFailingURLErrorKey;
FOUNDATION_EXPORT NSString *const NSURLErrorFailingURLStringErrorKey;
FOUNDATION_EXPORT NSString *const NSURLErrorBackgroundTaskCancelledReasonKey;
FOUNDATION_EXPORT NSString *const NSURLErrorNetworkUnavailableReasonKey;
FOUNDATION_EXPORT NSString *const NSURLSessionDownloadTaskResumeData;
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
@interface NSNumber (W71OverlayInits)
- (instancetype)initWithChar:(char)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithUnsignedChar:(unsigned char)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithShort:(short)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithUnsignedShort:(unsigned short)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithInt:(int)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithUnsignedInt:(unsigned int)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithLong:(long)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithUnsignedLong:(unsigned long)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithLongLong:(long long)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithUnsignedLongLong:(unsigned long long)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithFloat:(float)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithDouble:(double)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithBool:(BOOL)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithInteger:(NSInteger)value __attribute__((swift_name("init(value:)")));
- (instancetype)initWithUnsignedInteger:(NSUInteger)value __attribute__((swift_name("init(value:)")));
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
@interface NSSet<__covariant ObjectType> (W71OverlayAdditions)
- (instancetype)initWithObjects:(const ObjectType _Nonnull [_Nullable])objects count:(NSInteger)cnt;
- (instancetype)initWithArray:(NSArray *)array;
- (instancetype)initWithSet:(NSSet<ObjectType> *)set;
- (nullable ObjectType)member:(ObjectType)object;
- (BOOL)isEqualToSet:(NSSet<ObjectType> *)otherSet;
- (void)enumerateObjectsUsingBlock:(void (NS_NOESCAPE ^)(ObjectType obj, BOOL *stop))block __attribute__((swift_name("enumerateObjects(_:)")));
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
@interface NSString (W71OverlayAdditions)
- (nullable instancetype)initWithBytes:(const void *)bytes length:(NSInteger)len encoding:(NSStringEncoding)encoding;
- (nullable instancetype)initWithBytesNoCopy:(void *)bytes length:(NSInteger)len encoding:(NSStringEncoding)encoding freeWhenDone:(BOOL)freeBuffer;
- (instancetype)initWithString:(NSString *)aString;
- (instancetype)initWithFormat:(NSString *)format arguments:(va_list)argList NS_FORMAT_FUNCTION(1, 0);
- (instancetype)initWithFormat:(NSString *)format locale:(nullable id)locale arguments:(va_list)argList NS_FORMAT_FUNCTION(1, 0);
- (NSString *)stringByAppendingString:(NSString *)aString;
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
@interface NSURL (W71OverlayAdditions)
- (nullable instancetype)initWithString:(NSString *)URLString relativeToURL:(nullable NSURL *)baseURL;
- (instancetype)initFileURLWithPath:(NSString *)path isDirectory:(BOOL)isDir relativeToURL:(nullable NSURL *)baseURL;
- (instancetype)initFileURLWithPath:(NSString *)path relativeToURL:(nullable NSURL *)baseURL;
- (instancetype)initFileURLWithPath:(NSString *)path isDirectory:(BOOL)isDir;
- (instancetype)initFileURLWithPath:(NSString *)path;
- (instancetype)initAbsoluteURLWithDataRepresentation:(NSData *)data relativeToURL:(nullable NSURL *)baseURL;
- (instancetype)initWithDataRepresentation:(NSData *)data relativeToURL:(nullable NSURL *)baseURL;
+ (nullable instancetype)URLWithString:(NSString *)URLString relativeToURL:(nullable NSURL *)baseURL;
+ (instancetype)fileURLWithPath:(NSString *)path isDirectory:(BOOL)isDir relativeToURL:(nullable NSURL *)baseURL;
+ (instancetype)fileURLWithPath:(NSString *)path relativeToURL:(nullable NSURL *)baseURL;
+ (instancetype)fileURLWithPath:(NSString *)path isDirectory:(BOOL)isDir;
@property(readonly, copy) NSData *dataRepresentation;
@property(readonly, copy, nullable) NSURL *absoluteURL;
@property(readonly, copy, nullable) NSURL *baseURL;
@property(readonly, copy) NSString *relativeString;
@property(readonly, copy, nullable) NSString *relativePath;
@property(readonly, copy, nullable) NSNumber *port;
@property(readonly, copy, nullable) NSString *user;
@property(readonly, copy, nullable) NSString *password;
@property(readonly, copy, nullable) NSString *parameterString;
@property(readonly, copy, nullable) NSString *lastPathComponent;
@property(readonly, copy, nullable) NSString *pathExtension;
@property(readonly, copy, nullable) NSArray *pathComponents;
@property(readonly) BOOL hasDirectoryPath;
@property(readonly, copy, nullable) NSURL *standardizedURL;
@property(readonly, copy, nullable) NSURL *filePathURL;
@property(readonly, copy, nullable) NSURL *fileReferenceURL;
@property(readonly, copy, nullable) NSURL *URLByDeletingLastPathComponent;
@property(readonly, copy, nullable) NSURL *URLByDeletingPathExtension;
@property(readonly, copy, nullable) NSURL *URLByStandardizingPath;
@property(readonly, copy, nullable) NSURL *URLByResolvingSymlinksInPath;
- (BOOL)isFileReferenceURL;
- (nullable NSURL *)URLByAppendingPathComponent:(NSString *)pathComponent isDirectory:(BOOL)isDirectory;
- (nullable NSURL *)URLByAppendingPathExtension:(NSString *)pathExtension;
- (BOOL)checkResourceIsReachableAndReturnError:(NSError **)error __attribute__((swift_error(none)));
@property(readonly) const char *fileSystemRepresentation NS_RETURNS_INNER_POINTER;
- (instancetype)initFileURLWithFileSystemRepresentation:(const char *)path isDirectory:(BOOL)isDir relativeToURL:(nullable NSURL *)baseURL __attribute__((swift_name("init(fileURLWithFileSystemRepresentation:isDirectory:relativeTo:)")));
+ (instancetype)fileURLWithFileSystemRepresentation:(const char *)path isDirectory:(BOOL)isDir relativeToURL:(nullable NSURL *)baseURL;
@end
NS_ASSUME_NONNULL_END
NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT void NSGetSizeAndAlignment(const char *typePtr, NSUInteger * _Nullable sizep, NSUInteger * _Nullable alignp);
@interface NSValue (W71OverlayAdditions)
- (void)getValue:(void *)value;
/* NSInteger so the Swift importer sees Int, which is what the overlay sources pass (Apple's SDK apinotes map
   the NSUInteger parameter to Int as well); the ABI is the same register width. */
- (void)getValue:(void *)value size:(NSInteger)size;
- (instancetype)initWithBytes:(const void *)value objCType:(const char *)type;
+ (NSValue *)valueWithBytes:(const void *)value objCType:(const char *)type;
- (BOOL)isEqualToValue:(NSValue *)value;
@property(readonly) NSRange rangeValue;
+ (NSValue *)valueWithRange:(NSRange)range;
@end

NS_ASSUME_NONNULL_END
