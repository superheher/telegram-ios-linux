// tgbuild shim: the `os` module (`import os.log` resolves to a Swift module named `os`).
// The real os_log writes unified logging; this shim type-checks and no-ops — the app's
// diagnostics logging is not on the L3 critical path. Marker: tgbuild shim.
public struct OSLog {
    public init(subsystem: String, category: String) {}
    public static let `default` = OSLog(subsystem: "default", category: "default")
}

public struct OSLogType: RawRepresentable, Equatable {
    public let rawValue: UInt8
    public init(rawValue: UInt8) { self.rawValue = rawValue }
    public static let `default` = OSLogType(rawValue: 0)
    public static let info = OSLogType(rawValue: 1)
    public static let debug = OSLogType(rawValue: 2)
    public static let error = OSLogType(rawValue: 16)
    public static let fault = OSLogType(rawValue: 17)
}

public func os_log(_ message: StaticString, log: OSLog = .default, type: OSLogType = .default,
                   _ args: Any...) {}
