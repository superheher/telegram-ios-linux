// Stand-in for `swift_intent_library(name = "GeneratedSources")` (Telegram/SiriIntents/
// en.lproj/Intents.intentdefinition): Apple's intent codegen runs only on macOS, so the
// Linux build compiles these declarations directly. The class names and the @objc names
// must track the intentdefinition exactly (WidgetKit decodes widget configurations by
// them). Compiled by tools/tgbuild/make-generated-sources.sh into
// build-input/swift/modules + objects; Linked into TelegramUI.
import Intents

@objc(SelectFriendsIntent)
public class SelectFriendsIntent: INIntent {
    @NSManaged public var friends: [Friend]?
}

@objc(SelectAvatarFriendsIntent)
public class SelectAvatarFriendsIntent: INIntent {
    @NSManaged public var friends: [Friend]?
}

@objc(Friend)
public class Friend: INObject {
}
