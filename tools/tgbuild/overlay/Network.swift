import Foundation
import Dispatch

// tgbuild shim: the Network framework surface the app uses (`import Network`,
// NWPathMonitor path monitoring). The real implementation monitors system interfaces;
// this shim type-checks and reports unsatisfied until the L3 milestone wires it to
// reachability reality. Marker: tgbuild shim.
public class NWPathMonitor {
    private let _current = NWPath()
    public var pathUpdateHandler: ((NWPath) -> Void)?
    public var currentPath: NWPath { return _current }
    public init() {}
    public func start(queue: DispatchQueue) {}
    public func cancel() {}
}

public struct NWPath {
    public enum Status {
        case satisfied
        case unsatisfied
    }
    public enum InterfaceType {
        case wifi
        case cellular
        case wiredEthernet
        case loopback
    }
    public var status: Status { return .unsatisfied }
    public func usesInterfaceType(_ type: InterfaceType) -> Bool { return false }
}

// tgbuild shim, part 2: the TCP connection surface TelegramCore uses (`NWConnection`).
// Type-checks and no-ops the transport; real sockets arrive with the L3 milestone.
public final class NWProtocolTCP_Options {
    public var noDelay: Bool = false
    public var enableKeepalive: Bool = false
    public var keepaliveIdle: Double = 0
    public var keepaliveCount: Int = 0
    public var keepaliveInterval: Double = 0
    public var enableFastOpen: Bool = false
    public init() {}
}

public enum NWProtocolTCP {
    public static func Options() -> NWProtocolTCP_Options { return NWProtocolTCP_Options() }
}

public final class NWParameters {
    public var preferNoProxies: Bool = false
    public init() {}
    public init(tls: Any?, tcp: NWProtocolTCP_Options?) {}
}

public enum NWEndpoint {
    public enum Host {
        case name(String, String?)
        case ipv4(any Any)
        case ipv6(any Any)

        public init(_ name: String) {
            self = .name(name, nil)
        }
    }
    public enum Port: RawRepresentable, Equatable {
        case raw(UInt16)
        public var rawValue: UInt16 {
            switch self {
            case let .raw(v): return v
            }
        }
        public init?(rawValue: UInt16) { self = .raw(rawValue) }
    }
}

public final class NWConnection_ContentContext {
    public var isFinal: Bool { return false }
    public init() {}
}

public final class NWConnection {
    public enum State {
        case setup
        case waiting(Error)
        case preparing
        case ready
        case failed(Error)
        case cancelled
    }
    public enum SendCompletion {
        case contentProcessed((Error?) -> Void)
        case idempotent
    }

    public var stateUpdateHandler: ((State) -> Void)?
    public var viabilityUpdateHandler: ((Bool) -> Void)?
    public var pathUpdateHandler: ((NWPath) -> Void)?
    public var currentPath: NWPath { return NWPath() }
    public private(set) var currentState: State = .setup

    public init(host: NWEndpoint.Host, port: NWEndpoint.Port, using: NWParameters) {}

    public func start(queue: DispatchQueue) {}
    public func cancel() {}

    public func send(content: Data?, completion: SendCompletion) {
        if case let .contentProcessed(handler) = completion {
            handler(nil)
        }
    }

    public typealias ContentContext = NWConnection_ContentContext

    public func receive(minimumIncompleteLength: Int, maximumLength: Int,
                        completion: @escaping (Data?, NWConnection_ContentContext?, Bool, Error?) -> Void) {
        // No data arrives from the shim; receive stays pending rather than spinning
        // a caller's re-entrant read loop synchronously.
    }
}

extension NWConnection {
    public var path: NWPath { return NWPath() }
}

