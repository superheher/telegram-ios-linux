// tgbuild stub: the RecaptchaEnterprise vendor swiftinterface (built by Apple swift
// 6.2.3 with -enable-experimental-feature AccessLevelOnImport) does not parse under the
// OSS toolchain's ClangImporter — the parse drops the module's Swift declarations
// ("RecaptchaClient is unavailable: cannot find Swift declaration"). This stub declares
// the exact surface TelegramUI uses, compiled by OUR compiler, so AppDelegate
// type-checks; the bodies no-op, matching the shipped 28.10-31.10 builds which predate
// the recaptcha feature. The real framework binary stays unlinked — see link.py.
// Marker: tgbuild stub.
import Foundation

@objc public enum RecaptchaActionType: Int {
    case login
    case signup
    case other
}

@objc public enum RecaptchaErrorCode: Int {
    case errorCodeUnknown = 0
    case errorNetworkError = 1
    case errorInvalidSiteKey = 2
    case erroInvalidKeyType = 3
    case errorInvalidPackageName = 4
    case errorInvalidAction = 5
    case errorInvalidTimeout = 6
    case errorNoNetwork = 7
    case errorCodeInternalError = 100
}

@objc public class RecaptchaConstant: NSObject {
    @objc public static let clientVersion: String = ""
    @objc public static let defaultTimeoutExecute: Double = 10.0
    @objc public static let defaultTimeoutInit: Double = 10.0
}

@objc public class Recaptcha: NSObject {
    @objc public static func fetchClient(withSiteKey siteKey: String, completion: @escaping @Sendable (RecaptchaClient?, NSError?) -> Void) {
        completion(nil, nil)
    }

    @objc public static func getClient(withSiteKey siteKey: String, withTimeout timeout: Double, completion: @escaping @Sendable (RecaptchaClient?, NSError?) -> Void) {
        completion(nil, nil)
    }

    @objc public static func getClient(withSiteKey siteKey: String, completion: @escaping @Sendable (RecaptchaClient?, NSError?) -> Void) {
        completion(nil, nil)
    }

    @objc public static func getClient(siteKey: String, completionHandler: @escaping @Sendable (RecaptchaClient?, NSError?) -> Void) {
        completionHandler(nil, nil)
    }
}

@objc final public class RecaptchaAction: NSObject, @unchecked Sendable {
    @objc public init(action: RecaptchaActionType) {
        self.actionType = action
        super.init()
    }

    convenience public init(customAction: String) {
        self.init(action: .other)
    }

    @objc public static let login: RecaptchaAction = RecaptchaAction(action: .login)
    @objc public static let signup: RecaptchaAction = RecaptchaAction(action: .signup)
    @objc public static func custom(_ action: String) -> RecaptchaAction {
        return RecaptchaAction(customAction: action)
    }

    private let actionType: RecaptchaActionType
}

@objc final public class RecaptchaClient: NSObject, @unchecked Sendable {
    @objc public func execute(withAction action: RecaptchaAction, withTimeout timeout: Double, completion: @escaping @Sendable (String?, NSError?) -> Void) {
        completion(nil, nil)
    }

    @objc public func execute(withAction action: RecaptchaAction, completion: @escaping @Sendable (String?, NSError?) -> Void) {
        completion(nil, nil)
    }

    @objc public func execute(_ action: RecaptchaAction, completion: @escaping @Sendable (String?, NSError?) -> Void) {
        completion(nil, nil)
    }
}
