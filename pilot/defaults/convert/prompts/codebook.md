# Protocol: Create Conversion Codebook

Build the definitive reference document for converting this iOS app to
Flutter/Dart. Every conversion task will include this codebook in its
prompt — it's the consistency mechanism across hundreds of conversions.

## Signals
- `<signal:update>message</signal:update>` — progress
- `<signal:completed>summary</signal:completed>` — codebook written
- `<signal:failed>reason</signal:failed>` — fatal only

## Inputs

- **Analysis**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_ANALYSIS}}`
- **Inventory**: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_INVENTORY}}`
- **iOS source**: `{{var:PILOT_IOS_DIR}}/` (read specific files as needed)

## Output

Write to: `{{var:PILOT_CONFIG_DIR}}/{{var:PILOT_CODEBOOK}}`

## Execution

1. Read the analysis document thoroughly.
2. Read the inventory JSON for the dependency list.
3. `<signal:update>building codebook</signal:update>`
4. For each iOS dependency, find the best Flutter/pub.dev equivalent.
   Read the iOS source to understand HOW each dep is used — the
   replacement must cover the same use cases.
5. Map architectural patterns to Flutter equivalents.
6. Map iOS types and APIs to Dart equivalents.
7. Define the project structure for the Flutter app.
8. Write the codebook.

## Codebook Format

```markdown
# Conversion Codebook: [Project Name]

## Architecture Decisions

### State Management
[Choice: Riverpod / BLoC / Provider — and WHY for this specific app]

### Navigation
[Choice: go_router / auto_route — routing structure]

### Project Structure
```
lib/
  models/          # Data classes, DTOs, enums
  services/        # API clients, business logic
  repositories/    # Data access layer
  providers/       # State management
  screens/         # UI screens
  widgets/         # Reusable widgets
  utils/           # Helpers, extensions
  config/          # Constants, theme, routes
```

### Dependency Injection
[How services are provided — Riverpod providers, get_it, etc.]

## Dependency Mapping

| iOS (CocoaPod/SPM) | Flutter (pub.dev) | Notes |
|:--------------------|:-------------------|:------|
| Alamofire           | dio                | [specific API mappings] |
| Kingfisher          | cached_network_image | ... |
| Realm               | drift / hive       | ... |
| ...                 | ...                | ... |

## Type Mapping

| Swift | Dart | Notes |
|:------|:-----|:------|
| String | String | — |
| Int | int | — |
| Double | double | — |
| Bool | bool | — |
| Date / NSDate | DateTime | Use .toIso8601String() for serialization |
| Data | Uint8List | — |
| URL | Uri | — |
| Optional<T> / T? | T? | Same concept, different syntax |
| Array<T> / [T] | List<T> | — |
| Dictionary<K,V> | Map<K,V> | — |
| Set<T> | Set<T> | — |
| Any | dynamic | Avoid — prefer Object? where possible |
| Result<T, Error> | (use exceptions or Either) | ... |
| Codable | json_serializable / freezed | [chosen approach for this app] |

## Pattern Mapping

| iOS Pattern | Flutter/Dart Equivalent | Example |
|:------------|:------------------------|:--------|
| UIViewController | StatefulWidget / Screen | ... |
| UIView | Widget | Compose, don't inherit |
| UITableView / UICollectionView | ListView / GridView | ... |
| Delegate pattern | Callbacks / Streams | ... |
| KVO | ValueNotifier / StateNotifier | ... |
| NotificationCenter | Stream / EventBus / Provider | ... |
| Singleton | Riverpod provider / top-level | ... |
| Storyboard segue | GoRouter route | ... |
| IBOutlet / IBAction | (N/A — widget tree) | ... |
| CoreData NSManagedObject | drift Table / hive TypeAdapter | ... |
| UserDefaults | SharedPreferences | ... |
| Keychain | flutter_secure_storage | ... |
| UIColor | Color | ... |
| UIFont | TextStyle | ... |
| UIImage | Image widget / AssetImage | ... |
| NSError / Error | Exception | ... |
| Grand Central Dispatch | async/await / Isolate | ... |
| Combine Publisher | Stream / Riverpod | ... |
| Protocol (Swift) | abstract class / interface | ... |
| Extension (Swift) | extension (Dart) | Same concept |
| Enum with associated values | sealed class (Dart 3) | ... |
| Struct (value type) | freezed / data class | ... |
| Guard statement | Early return with if | ... |
| Optional chaining (x?.y?.z) | Same in Dart (x?.y?.z) | ... |

## Naming Conventions

| iOS | Dart |
|:----|:-----|
| UpperCamelCase (types) | UpperCamelCase (types) |
| lowerCamelCase (methods, vars) | lowerCamelCase (methods, vars) |
| kConstantName | kConstantName or SCREAMING_SNAKE |
| _privateVar | _privateVar (file-private) |
| protocol FooDelegate | abstract class FooListener |

## Anti-Patterns — Do NOT

- Don't create God widgets — split into smaller widgets
- Don't use setState for complex state — use the chosen state management
- Don't put business logic in widgets — keep it in services/providers
- Don't translate UIKit view hierarchy 1:1 — think in Flutter composition
- Don't use dynamic where a type is known
- Don't ignore null safety — use required, late, or provide defaults

## Conversion Order

1. **Data models & DTOs** (pure Dart, no Flutter dependency)
2. **Enums & constants** (pure Dart)
3. **Utilities & extensions** (pure Dart)
4. **Networking / API layer** (dio, mostly pure Dart)
5. **Services & business logic** (pure Dart + packages)
6. **Repositories / data access** (persistence layer)
7. **State management / providers** (Riverpod/BLoC)
8. **Navigation & routing** (go_router setup)
9. **Reusable widgets** (shared UI components)
10. **Screens** (feature UI, one feature at a time)
11. **App shell** (main.dart, theme, top-level providers)
```

## Rules

| Rule | Constraint |
|:-----|:-----------|
| Be specific to this app | Don't write a generic Swift→Dart guide. Reference actual classes and patterns from the analysis |
| Justify architecture | State management, nav, DI — explain WHY each choice fits this app |
| Complete dep mapping | Every CocoaPod/SPM dep must have a Flutter equivalent (or "platform channel needed") |
| Layer-first order | Models → services → UI. This is the conversion order |
| Testable patterns | Chosen patterns must be testable (injectable deps, pure business logic) |
| This doc will evolve | The reflect stage updates this codebook as the conversion progresses |
