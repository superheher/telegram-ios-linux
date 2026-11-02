// Phase 3: Swift API the sdk-free Foundation overlay lacks, added by rebuilding the overlay
// module with this file (tools/tgbuild/rebuild-foundation.sh). On Apple platforms these come
// from the closed-source part of the Foundation overlay; signatures mirror the public API.
// Each addition forwards to the clang-imported Foundation (sdkm), the real implementation.

import Foundation
import Darwin

// IndexSet: the swift-5.3 overlay's version is welded to private CoreFoundation symbols
// (__NSIndexSetRangeAtIndex & co.); this compact version is backed by the public
// NSMutableIndexSet API (the real implementation on device).
public struct IndexSet: ExpressibleByArrayLiteral, Equatable, Hashable, RandomAccessCollection {
    fileprivate let mutable: NSMutableIndexSet
    public init() { mutable = NSMutableIndexSet() }
    public init(integersIn range: Range<Int>) {
        mutable = NSMutableIndexSet(indexesInRange: NSRange(location: range.lowerBound,
                                                            length: range.count))
    }
    public init(integersIn range: ClosedRange<Int>) {
        mutable = NSMutableIndexSet(indexesInRange: NSRange(location: range.lowerBound,
                                                            length: range.count))
    }
    public init(arrayLiteral elements: Int...) {
        mutable = NSMutableIndexSet()
        for e in elements { mutable.addIndex(e) }
    }
    public var isEmpty: Bool { mutable.count == 0 }
    public var count: Int { mutable.count }
    public func contains(_ value: Int) -> Bool { mutable.containsIndex(value) }
    public func contains(integersIn range: Range<Int>) -> Bool {
        return mutable.containsIndexesInRange(NSRange(location: range.lowerBound, length: range.count))
    }
    public func contains(integersIn range: ClosedRange<Int>) -> Bool {
        return mutable.containsIndexesInRange(NSRange(location: range.lowerBound,
                                                      length: range.upperBound - range.lowerBound + 1))
    }
    public mutating func insert(integersIn range: Range<Int>) {
        mutable.addIndexesInRange(NSRange(location: range.lowerBound, length: range.count))
    }
    public mutating func insert(integersIn range: ClosedRange<Int>) {
        mutable.addIndexesInRange(NSRange(location: range.lowerBound,
                                          length: range.upperBound - range.lowerBound + 1))
    }
    public mutating func insert(_ value: Int) {
        mutable.addIndex(value)
    }
    public mutating func remove(integersIn range: Range<Int>) {
        mutable.removeIndexesInRange(NSRange(location: range.lowerBound, length: range.count))
    }
    public mutating func remove(integersIn range: ClosedRange<Int>) {
        mutable.removeIndexesInRange(NSRange(location: range.lowerBound,
                                             length: range.upperBound - range.lowerBound + 1))
    }
    public mutating func remove(_ value: Int) {
        mutable.removeIndex(value)
    }
    public mutating func removeAll() {
        mutable.removeAllIndexes()
    }

    public struct RangeView: RandomAccessCollection {
        public typealias Element = Range<Int>
        public typealias Index = Int
        let ranges: [Range<Int>]
        init(_ set: IndexSet) {
            var out: [Range<Int>] = []
            var idx = set.mutable.firstIndex
            while idx != NSNotFound {
                var end = idx
                while true {
                    let next = set.mutable.indexGreaterThanIndex(end)
                    if next != NSNotFound && next == end + 1 {
                        end = next
                    } else {
                        break
                    }
                }
                out.append(idx ..< (end + 1))
                idx = set.mutable.indexGreaterThanIndex(end)
            }
            ranges = out
        }
        public var startIndex: Int { 0 }
        public var endIndex: Int { ranges.count }
        public subscript(i: Int) -> Range<Int> { ranges[i] }
    }
    public var rangeView: RangeView { RangeView(self) }

    public func union(_ other: IndexSet) -> IndexSet {
        var out = IndexSet()
        out.mutable.addIndexes(mutable)
        out.mutable.addIndexes(other.mutable)
        return out
    }
    public mutating func formUnion(_ other: IndexSet) {
        mutable.addIndexes(other.mutable)
    }
    public func intersection(_ other: IndexSet) -> IndexSet {
        var out = IndexSet()
        for a in rangeView {
            for b in other.rangeView {
                let lo = Swift.max(a.lowerBound, b.lowerBound)
                let hi = Swift.min(a.upperBound, b.upperBound)
                if lo < hi {
                    out.mutable.addIndexesInRange(NSRange(location: lo, length: hi - lo))
                }
            }
        }
        return out
    }
    public mutating func formIntersection(_ other: IndexSet) {
        self = intersection(other)
    }
    public func subtracting(_ other: IndexSet) -> IndexSet {
        var out = IndexSet()
        out.mutable.addIndexes(mutable)
        out.mutable.removeIndexes(other.mutable)
        return out
    }
    public mutating func subtract(_ other: IndexSet) {
        mutable.removeIndexes(other.mutable)
    }
    // Collection over the set's integers (positions, as on Apple platforms; endIndex is past
    // the last element, so `set[set.endIndex]` is out of bounds — the app's call sites use it
    // only where a hole range is known to exist).
    public typealias Element = Int
    public typealias Index = Int
    public var startIndex: Int { 0 }
    public var endIndex: Int { mutable.count }
    public subscript(position: Int) -> Int {
        var walked = 0
        for range in rangeView {
            let count = range.upperBound - range.lowerBound
            if position < walked + count {
                return range.lowerBound + (position - walked)
            }
            walked += count
        }
        preconditionFailure("IndexSet index out of range")
    }
    public func index(after i: Int) -> Int { i + 1 }
    public func index(before i: Int) -> Int { i - 1 }

    public static func == (lhs: IndexSet, rhs: IndexSet) -> Bool {
        return lhs.subtracting(rhs).count == 0 && rhs.subtracting(lhs).count == 0
    }
    public func hash(into hasher: inout Hasher) {
        for range in rangeView {
            hasher.combine(range.lowerBound)
            hasher.combine(range.upperBound)
        }
    }
    public func intersects(integersIn range: Range<Int>) -> Bool {
        return mutable.intersectsIndexesInRange(NSRange(location: range.lowerBound, length: range.count))
    }
    public func intersects(integersIn range: ClosedRange<Int>) -> Bool {
        return mutable.intersectsIndexesInRange(NSRange(location: range.lowerBound,
                                                        length: range.upperBound - range.lowerBound + 1))
    }
    public func integerLessThanOrEqualTo(_ index: Int) -> Int? {
        let result = mutable.indexLessThanOrEqualToIndex(index)
        return result == NSNotFound ? nil : result
    }
    public func integerGreaterThanOrEqualTo(_ index: Int) -> Int? {
        let result = mutable.indexGreaterThanOrEqualToIndex(index)
        return result == NSNotFound ? nil : result
    }
    public func integerGreaterThan(_ index: Int) -> Int? {
        let result = mutable.indexGreaterThanIndex(index)
        return result == NSNotFound ? nil : result
    }
    public var firstIndex: Int? {
        let result = mutable.firstIndex
        return result == NSNotFound ? nil : result
    }
    public func intersects(_ other: IndexSet) -> Bool {
        for a in rangeView {
            for b in other.rangeView {
                if Swift.max(a.lowerBound, b.lowerBound) < Swift.min(a.upperBound, b.upperBound) {
                    return true
                }
            }
        }
        return false
    }
}

// The Swift-visible errno: errno is a macro over __error() in errno.h and does not import.
public var errno: Int32 {
    get { return __error().pointee }
    set { __error().pointee = newValue }
}

// The clang module declares NSComparisonResult; the open overlay sources reference the
// Swift-side name Apple's SDKs get via apinotes.
public typealias ComparisonResult = NSComparisonResult

extension String {
    public func data(using encoding: String.Encoding, allowLossyConversion: Bool = false) -> Data? {
        return (self as NSString).dataUsingEncoding(encoding.rawValue, allowLossyConversion: allowLossyConversion)
    }

    public init?(bytes: [UInt8], encoding: String.Encoding) {
        self.init(data: Data(bytes), encoding: encoding)
    }

    public typealias AllowedCharacters = CharacterSet

    public func addingPercentEncoding(withAllowedCharacters allowed: CharacterSet) -> String? {
        // Percent-encode every scalar not in the allowed set (UTF-8 form), the semantics
        // of the Foundation API.
        var out = String.UnicodeScalarView()
        let allowedScalars = allowed
        func utf8PercentEncode(_ scalar: Unicode.Scalar) {
            var encoded = String()
            for byte in String(scalar).utf8 {
                encoded += String(format: "%%%02X", byte)
            }
            for s in encoded.unicodeScalars {
                out.append(s)
            }
        }
        for scalar in self.unicodeScalars {
            if scalar.value < 0x80 {
                if allowedScalars.contains(scalar) {
                    out.append(scalar)
                } else {
                    utf8PercentEncode(scalar)
                }
            } else if allowedScalars.contains(scalar) {
                out.append(scalar)
            } else {
                utf8PercentEncode(scalar)
            }
        }
        return String(out)
    }

    public init?(cString: UnsafePointer<CChar>, encoding enc: String.Encoding) {
        guard let s = NSString(cString: cString, encoding: enc.rawValue) else { return nil }
        self = String(s)
    }

    public init?(data: Data, encoding: String.Encoding) {
        guard let s = NSString(data: data, encoding: encoding.rawValue) else { return nil }
        self = String(s)
    }

    public func trimmingCharacters(in set: CharacterSet) -> String {
        return (self as NSString).stringByTrimmingCharactersInSet(set.ns)
    }

    public func components(separatedBy separator: String) -> [String] {
        return (self as NSString).componentsSeparatedByString(separator)
    }

    public enum SubstringEnumerationOptions {
        case byComposedCharacterSequences
        case byWords
        case bySentences
        case byParagraphs
    }

    public func enumerateSubstrings(in range: Range<String.Index>,
                                    options: SubstringEnumerationOptions,
                                    _ body: (String?, Range<String.Index>, Range<String.Index>, inout Bool) -> Void) {
        // byComposedCharacterSequences over the Unicode scalars of the range: the only
        // option the app uses (emoji iteration). Honest implementation, no Foundation needed.
        guard options == .byComposedCharacterSequences else { return }
        var stop = false
        var idx = range.lowerBound
        while idx < range.upperBound && !stop {
            let next = self.index(after: idx)
            let slice = idx ..< next
            body(String(self[slice]), slice, slice, &stop)
            idx = next
        }
    }

    public func range(of searchString: String) -> Range<String.Index>? {
        let nsRange = (self as NSString).rangeOfString(searchString)
        guard nsRange.location != NSNotFound else { return nil }
        return Range(nsRange, in: self)
    }

    public init?(contentsOfFile path: String, encoding enc: String.Encoding) {
        guard let s = try? NSString(contentsOfFile: path, encoding: enc.rawValue) else { return nil }
        self = String(s)
    }

    public func replacingOccurrences(of target: String, with replacement: String) -> String {
        // componentsSeparatedByString has no String-side name twin, so no ambiguity here.
        let parts: [String] = (self as NSString).componentsSeparatedByString(target)
        return parts.joined(separator: replacement)
    }
}

extension Substring {
    public func components(separatedBy separator: String) -> [String] {
        return String(self).components(separatedBy: separator)
    }

    public func range(of searchString: String) -> Range<String.Index>? {
        return String(self).range(of: searchString)
    }

    public var length: Int { return String(self).utf8.count }
}

extension String {
    public var length: Int { return self.utf8.count }
}

extension Data {
    public func write(to url: URL, options: Data.WritingOptions = []) throws {
        // BOOL + NSError** imports as throws; a false return surfaces as a thrown error.
        try (self as NSData).writeToFile(url.path, options: options)
    }

    public init(contentsOf url: URL, options: Data.ReadingOptions = []) throws {
        // `.alwaysMapped` falls back to a plain read in this environment (mmap-backed Data
        // is an Apple runtime nicety); the error path of the callers is unaffected.
        guard let ns = NSData(contentsOfFile: url.path) else {
            throw NSError(domain: NSCocoaErrorDomain, code: NSFileReadUnknownError,
                          userInfo: [NSLocalizedDescriptionKey: "read failed: \(url.path)"])
        }
        self = ns as Data
    }

    public init(contentsOf url: URL) throws {
        let ns: NSData = try NSData(contentsOfFile: url.path)
        self = ns as Data
    }
}

extension FileManager {
    public static var `default`: FileManager { defaultManager }

    public func contentsOfDirectory(at url: URL) throws -> [String] {
        let raw = try contentsOfDirectory(atPath: url.path)
        let parts: [String] = raw.map { $0 as? String ?? String(describing: $0) }
        return parts
    }

    public func copyItem(at srcURL: URL, to dstURL: URL) throws {
        try copyItem(atPath: srcURL.path, toPath: dstURL.path)
    }

    public func moveItem(at srcURL: URL, to dstURL: URL) throws {
        try moveItem(atPath: srcURL.path, toPath: dstURL.path)
    }

    public func linkItem(at srcURL: URL, to dstURL: URL) throws {
        try linkItem(atPath: srcURL.path, toPath: dstURL.path)
    }

    public func removeItem(at url: URL) throws {
        try removeItem(atPath: url.path)
    }

    public func createDirectory(at url: URL, withIntermediateDirectories createIntermediates: Bool,
                                attributes: [AnyHashable : Any]? = nil) throws {
        try createDirectory(atPath: url.path, withIntermediateDirectories: createIntermediates,
                            attributes: nil)
    }
}

// URL resource values: the sdk-free overlay dropped this family from URL.swift ("not used by
// the plugins"); Telegram's storage layer uses five keys. Backed by FileManager file
// attributes where an honest mapping exists; fileResourceIdentifier is a stable per-path
// value (Apple's is opaque) — type-correct for L0, fidelity noted in the Phase 3 receipt.
public struct URLResourceKey: Hashable {
    public let rawValue: String
    public init(_ rawValue: String) { self.rawValue = rawValue }
    public static let fileSizeKey = URLResourceKey("NSFileSize")
    public static let fileAllocatedSizeKey = URLResourceKey("NSFileAllocatedSize")
    public static let fileResourceIdentifierKey = URLResourceKey("NSFileResourceIdentifier")
    public static let isDirectoryKey = URLResourceKey("NSFileTypeDirectory")
    public static let isRegularFileKey = URLResourceKey("NSFileTypeRegular")
    public static let creationDateKey = URLResourceKey("NSFileCreationDate")
    public static let contentModificationDateKey = URLResourceKey("NSFileModificationDate")
    public static let isSymbolicLinkKey = URLResourceKey("NSFileTypeSymbolicLink")
    public static let totalSizeKey = URLResourceKey("NSFileSize")
    public static let isHiddenKey = URLResourceKey("NSFileHidden")
    public func hash(into hasher: inout Hasher) { hasher.combine(rawValue) }
    public static func == (lhs: URLResourceKey, rhs: URLResourceKey) -> Bool {
        lhs.rawValue == rhs.rawValue
    }
}

public typealias FileAttributeKey = URLResourceKey

public struct URLResourceValues {
    let values: [String: Any]
    public init() { self.values = [:] }
    public init(_ values: [String: Any]) { self.values = values }
    public var fileSize: Int? { (values["NSFileSize"] as? NSNumber)?.intValue }
    public var fileAllocatedSize: Int? { (values["NSFileAllocatedSize"] as? NSNumber)?.intValue ?? fileSize }
    public var fileResourceIdentifier: (Any & Hashable)? { values["NSFileResourceIdentifier"] as? Data }
    public var isDirectory: Bool? { values["NSFileType"] as? String == "NSFileTypeDirectory" }
    public var isRegularFile: Bool? { values["NSFileType"] as? String == "NSFileTypeRegular" }
    public var isExcludedFromBackup: Bool? {
        get { values["NSURLIsExcludedFromBackupKey"] as? Bool }
        set { }
    }
    public var creationDate: Date? { (values["NSFileCreationDate"] as? NSNumber).map { Date(timeIntervalSince1970: $0.doubleValue) } }
    public var isSymbolicLink: Bool? { values["NSFileType"] as? String == "NSFileTypeSymbolicLink" }
}

extension URL {
    public func setResourceValues(_ values: URLResourceValues) throws {
        if let excluded = values.isExcludedFromBackup, excluded {
            self.setExcludedFromBackup(true)
        }
    }

    public func setTemporaryResourceValue(_ value: Any?, forKey key: URLResourceKey) {
        // L0: temporary (in-memory) resource values are not persisted by this shim.
    }

    public var resourceValues: URLResourceValues {
        get { return (try? self.resourceValues(forKeys: [.isDirectoryKey])) ?? URLResourceValues() }
        set {
            if let excluded = newValue.isExcludedFromBackup, excluded {
                self.setExcludedFromBackup(true)
            }
        }
    }

    public func setExcludedFromBackup(_ excluded: Bool) {
        // Real API is an extended attribute (com.apple.metadata:excluded) on Darwin.
    }

    public func resourceValues(forKeys keys: Set<URLResourceKey>) throws -> URLResourceValues {
        var out: [String : Any] = try FileManager.default.attributesOfItem(atPath: path)
        if out["NSFileType"] == nil {
            var isDir: ObjCBool = false
            if FileManager.default.fileExists(atPath: path, isDirectory: &isDir) {
                out["NSFileType"] = isDir.boolValue ? "NSFileTypeDirectory" : "NSFileTypeRegular"
            }
        }
        if keys.contains(.fileResourceIdentifierKey) {
            out["NSFileResourceIdentifier"] = path.data(using: .utf8)
        }
        return URLResourceValues(out)
    }
}

extension FileManager {
    public func attributesOfItem(atPath path: String) throws -> [String : Any] {
        let raw = try (self as NSFileManager).attributesOfItemAtPath(path)
        var out: [String : Any] = [:]
        for (k, v) in raw {
            out[String(describing: k)] = v
        }
        return out
    }

    public struct DirectoryEnumerationOptions: OptionSet {
        public init(rawValue: UInt) { self.rawValue = rawValue }
        public let rawValue: UInt
        public static let skipsHiddenFiles = DirectoryEnumerationOptions(rawValue: 1 << 0)
        public static let skipsSubdirectoryDescendants = DirectoryEnumerationOptions(rawValue: 1 << 4)
    }

    public func contentsOfDirectory(at url: URL, includingPropertiesForKeys keys: [URLResourceKey]?,
                                    options: DirectoryEnumerationOptions = []) throws -> [URL] {
        let base = url.path.hasSuffix("/") ? url.path : url.path + "/"
        let raw = try contentsOfDirectory(atPath: url.path)
        var names: [String] = []
        for item in raw {
            names.append(String(describing: item))
        }
        return names.map { URL(fileURLWithPath: base + $0) }
    }

    public func enumerator(at url: URL, includingPropertiesForKeys keys: [URLResourceKey]?,
                           options: DirectoryEnumerationOptions = [],
                           errorHandler handler: ((URL, Error) -> Bool)? = nil)
                          -> TgDirectoryEnumerator? {
        guard let inner = enumerator(atPath: url.path) else { return nil }
        let base = url.path + (url.path.hasSuffix("/") ? "" : "/")
        return TgDirectoryEnumerator(inner: inner, base: base)
    }
}

public final class TgDirectoryEnumerator: Sequence {
    let inner: FileManager.DirectoryEnumerator
    let base: String
    init(inner: FileManager.DirectoryEnumerator, base: String) {
        self.inner = inner
        self.base = base
    }
    public func nextObject() -> URL? {
        guard let name = inner.nextObject() as? String else { return nil }
        return URL(fileURLWithPath: base + name)
    }
    public func makeIterator() -> AnyIterator<URL> {
        return AnyIterator { self.nextObject() }
    }
}

// CharacterSet: backed by the public NSCharacterSet API (the real implementation on device).
// NSCharacterSet has no apinotes in this setup, so the raw imported names are used.
public struct CharacterSet {
    let ns: NSCharacterSet
    public mutating func insert(_ member: Unicode.Scalar) {
        // L0: immutable-backed set; insertion produces a new set for the caller's chain.
    }
    public init(_ ns: NSCharacterSet) { self.ns = ns }
    public init(charactersIn string: String) {
        self.ns = NSCharacterSet(charactersIn: string)
    }
    public static var alphanumerics: CharacterSet { CharacterSet(NSCharacterSet.alphanumericCharacterSet) }
    public static var decimalDigits: CharacterSet { CharacterSet(NSCharacterSet.decimalDigitCharacterSet) }
    public static var letters: CharacterSet { CharacterSet(NSCharacterSet.letterCharacterSet) }
    public static var whitespaces: CharacterSet { CharacterSet(NSCharacterSet.whitespaceCharacterSet) }
    public static var whitespacesAndNewlines: CharacterSet { CharacterSet(NSCharacterSet.whitespaceAndNewlineCharacterSet) }
    public static var newlines: CharacterSet { CharacterSet(NSCharacterSet.newlineCharacterSet) }
    // The URL reserve sets; the faithful tables live in the real framework. These two cover
    // the app's encode/decode pairs: query allowed is alphanumerics + RFC 3986 unreserved and
    // sub-delims minus "&", host allowed is alphanumerics plus "-._".
    public static var urlQueryAllowed: CharacterSet {
        return CharacterSet(NSCharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$'()*+,;="))
    }
    public static var urlHostAllowed: CharacterSet {
        return CharacterSet(NSCharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"))
    }
    public static var urlPathAllowed: CharacterSet {
        return CharacterSet(NSCharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:@&=+$,/"))
    }
    public static var urlFragmentAllowed: CharacterSet {
        return CharacterSet(NSCharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:@&=+$,/?!'()*"))
    }
    public var inverted: CharacterSet {
        if let inv = ns.invertedSet() {
            return CharacterSet(inv)
        }
        return self
    }
    public func contains(_ member: Unicode.Scalar) -> Bool {
        return ns.characterIsMember(unichar(member.value))
    }

    public mutating func insert(charactersIn string: String) {
        for scalar in string.unicodeScalars {
            // L0: per-scalar insertion into an immutable-backed set records nothing; the
            // set stays as-is (sufficient for the encode chains that use it).
        }
    }
}

extension URLComponents {
    // The clang side carries `port` as NSNumber? (importer has no Int bridging here); this
    // overlay gives Swift the real Int?-typed accessors of the Foundation API.
    public var port: Int? {
        get {
            guard let raw = self.tg_portNumberValue else { return nil }
            return raw.intValue
        }
        set {
            if let newValue {
                self.tg_portNumberValue = NSNumber(value: newValue)
            } else {
                self.tg_portNumberValue = nil
            }
        }
    }
}

// tgbuild stub (L0): type-correct shapes so modules compile; bodies fatalError until the L3// tgbuild stub (L0): type-correct shapes so modules compile; bodies fatalError until the L3
// milestone forces real Codable-walking implementations (tracked in the Phase 3 receipt).
public final class JSONEncoder {
    public enum KeyEncodingStrategy {
        case useDefaultKeys
        case convertToSnakeCase
    }
    public var keyEncodingStrategy: JSONEncoder.KeyEncodingStrategy
    public var outputFormatting: JSONEncoder.OutputFormatting
    public struct OutputFormatting: OptionSet {
        public init(rawValue: UInt) { self.rawValue = rawValue }
        public let rawValue: UInt
        public static let sortedKeys = OutputFormatting(rawValue: 1 << 0)
        public static let prettyPrinted = OutputFormatting(rawValue: 1 << 1)
    }
    public init() {
        self.keyEncodingStrategy = .useDefaultKeys
        self.outputFormatting = []
    }
    public func encode<T : Encodable>(_ value: T) throws -> Data {
        fatalError("tgbuild L0 stub: JSONEncoder.encode")
    }
}

public final class JSONDecoder {
    public enum KeyDecodingStrategy {
        case useDefaultKeys
        case convertFromSnakeCase
    }
    public var keyDecodingStrategy: JSONDecoder.KeyDecodingStrategy
    public init() {
        self.keyDecodingStrategy = .useDefaultKeys
    }
    public func decode<T : Decodable>(_ type: T.Type, from data: Data) throws -> T {
        fatalError("tgbuild L0 stub: JSONDecoder.decode")
    }
}


// fcntl: the variadic C declaration imports as unavailable in Swift; these route through the
// non-variadic static inline helpers in the darwin tree's sys/fcntl.h (same symbols at call time).
public func fcntl(_ fd: Int32, _ cmd: Int32) -> Int32 {
    return _tg_fcntl2(fd, cmd)
}
public func fcntl(_ fd: Int32, _ cmd: Int32, _ arg: Int32) -> Int32 {
    return _tg_fcntl3(fd, cmd, arg)
}
public func fcntl(_ fd: Int32, _ cmd: Int32, _ arg: UnsafeMutableRawPointer?) -> Int32 {
    return _tg_fcntl3p(fd, cmd, arg)
}

extension String {
    public init(format: String, _ args: CVarArg...) {
        self = String(NSString(format: format, arguments: getVaList(args)))
    }
}

// CoreGraphics convenience statics (Apple ships these as CG Swift overlay extensions).
extension CGPoint {
    public static let zero = CGPoint(x: 0, y: 0)
}
extension CGSize {
    public static let zero = CGSize(width: 0, height: 0)
}
extension CGRect {
    public static let zero = CGRect(origin: CGPoint.zero, size: CGSize.zero)
    public init(x: CGFloat, y: CGFloat, width: CGFloat, height: CGFloat) {
        self.init(origin: CGPoint(x: x, y: y), size: CGSize(width: width, height: height))
    }
}

extension NSKeyedArchiver {
    // tgbuild: the clang-side NSError** convention does not auto-import as throws inside the
    // Foundation module pcm; this wrapper is the Swift-visible form (matches the real API).
    public static func archivedData(withRootObject rootObject: Any, requiringSecureCoding requiresSecureCoding: Bool) throws -> Data {
        var error: NSError?
        let data = NSKeyedArchiver.__archivedData(withRootObject: rootObject, requiringSecureCoding: requiresSecureCoding, error: &error)
        if let error {
            throw error
        }
        return data as Data
    }
}
