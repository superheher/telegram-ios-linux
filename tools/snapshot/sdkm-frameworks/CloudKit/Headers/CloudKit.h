/* Authored for the SDK-free sysroot (not Apple's file): the CloudKit public API subset the
   app uses, faithful to the real header (full headers arrive with the Phase 0 SDK). */
#ifndef CLOUDKIT_H
#define CLOUDKIT_H
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

__attribute__((swift_name("CKRecord.ID"))) @interface CKRecordID : NSObject <NSCopying, NSSecureCoding>
- (instancetype)initWithRecordName:(NSString *)recordName;
@property (readonly, copy) NSString *recordName;
@end

@interface CKRecord : NSObject <NSSecureCoding>
typedef NSString CKRecordKey;
- (instancetype)initWithRecordType:(NSString *)recordType recordID:(CKRecordID *)recordID;
@property (readonly, copy) NSString *recordType;
@property (readonly, strong) CKRecordID *recordID;
- (nullable id)objectForKey:(NSString *)key;
- (void)setObject:(nullable id)obj forKey:(NSString *)key;
@end

typedef NS_ENUM(NSInteger, CKDatabaseScope) {
    CKDatabaseScopePublic = 1,
    CKDatabaseScopePrivate = 2,
    CKDatabaseScopeShared = 3,
};

@interface CKDatabase : NSObject
- (void)fetchRecordWithType:(NSString *)recordType
                 identifier:(CKRecordID *)recordID
          completionHandler:(void (^)(CKRecord * _Nullable record, NSError * _Nullable error))completionHandler;
- (void)fetchRecordWithID:(CKRecordID *)recordID
        completionHandler:(void (^)(CKRecord * _Nullable record, NSError * _Nullable error))completionHandler
    __attribute__((swift_name("fetch(withRecordID:completionHandler:)")));
- (CKDatabase *)databaseWithDatabaseScope:(CKDatabaseScope)scope
    __attribute__((swift_name("database(with:)")));
@end

typedef NS_ENUM(NSInteger, CKErrorCode) {
    CKErrorInternalError = 1,
    CKErrorPartialFailure = 2,
    CKErrorNetworkUnavailable = 3,
    CKErrorNetworkFailure = 4,
    CKErrorBadContainer = 5,
    CKErrorServiceUnavailable = 6,
    CKErrorRequestRateLimited = 7,
    CKErrorMissingEntitlement = 8,
    CKErrorNotAllowed = 9,
    CKErrorPermissionFailure = 10,
    CKErrorUnknownItem = 11,
    CKErrorInvalidArguments = 12,
};

@interface CKError : NSObject
@property(class, readonly, copy) NSString *errorDomain;
@end

@interface CKContainer : NSObject
+ (CKContainer *)defaultContainer __attribute__((swift_name("default()")));
+ (CKContainer *)containerWithIdentifier:(nullable NSString *)identifier __attribute__((swift_name("init(identifier:)")));
- (CKDatabase *)databaseWithDatabaseScope:(CKDatabaseScope)scope __attribute__((swift_name("database(with:)")));
@end

NS_ASSUME_NONNULL_END
#endif
