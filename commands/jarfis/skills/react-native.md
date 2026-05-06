# React Native Expertise

> Cross-platform mobile (iOS/Android) with JS bridge — RN core, Hermes/Metro, navigation, native modules, performance.

## Core Patterns

### Runtime & Bundler
- **Hermes**: default JS engine since RN 0.70. Faster startup, lower memory, ahead-of-time bytecode. Verify with `global.HermesInternal != null`.
- **Metro**: bundler — watches FS via `metro.config.js`. FastRefresh preserves component state on edit; full reload required for native module changes.
- **JSI / TurboModules / Fabric**: New Architecture replaces the old async bridge with synchronous JSI calls. Opt-in via `newArchEnabled=true` (Android `gradle.properties`) + `RCT_NEW_ARCH_ENABLED=1` (iOS Podfile).

### Navigation (React Navigation 6/7)
- **Stack**: native-stack (`@react-navigation/native-stack`) uses platform navigators (UINavigationController / Fragment) — better gestures + perf than the JS-only stack
- **Tab**: bottom-tabs for primary nav; material-top-tabs for swipeable sub-sections
- **Drawer**: side menu — sparingly, hides discoverability on mobile

### Platform-Specific Code
- `Platform.select({ ios: ..., android: ..., default: ... })` for inline branches
- File suffixes `.ios.tsx` / `.android.tsx` — Metro auto-resolves based on bundle target
- `Platform.OS === 'ios'` cheap, but prefer `.ios.tsx` split when a component diverges in >3 places

## Decision Heuristics

- **State**: useState/Reducer for local; Zustand for shared client state (smallest bundle, no Provider); Redux Toolkit only when sagas/middleware are essential. Jotai works but RN devtools support is weaker than web.
- **List**: `FlashList` (Shopify) > `FlatList` for 100+ rows or heterogeneous heights — recycles cells via cell reuse (UICollectionView-style). FlatList ok for short, fixed-height lists.
- **Animation**: `react-native-reanimated` (worklet on UI thread) for any 60fps interaction; LayoutAnimation only for simple enter/exit; Animated API legacy.
- **OTA**: CodePush for bare RN; Expo Updates for Expo. JS-only changes ship OTA; native module / asset changes still require store review.

## Anti-patterns

- `setState` inside `onScroll` / `onMomentumScroll` — JS thread chokes. Use Reanimated `useAnimatedScrollHandler` (UI thread).
- Heavy computation in render — drops frames. Memoize with `useMemo` or move to a worklet.
- Inline arrow function as `FlatList` `renderItem` — recreates per render, defeats `keyExtractor` memoization. Define stable callback with `useCallback`.
- Direct `console.log` in hot paths — Hermes still serializes; bridge JSON cost. Strip in release via `babel-plugin-transform-remove-console`.
- Calling `Alert.alert` from a worklet — UI thread can't reach JS APIs. Use `runOnJS`.

## Version & Environment Notes

- **RN 0.74+**: Hermes default; New Arch opt-in stable
- **iOS**: Xcode 15+ for RN 0.74+; Podfile `min_ios_version_supported = 13.4`
- **Android**: `compileSdkVersion 34`, NDK 26 for RN 0.74; Hermes prebuilt for arm64-v8a + armeabi-v7a + x86_64
- **Expo SDK 50+**: aligns to RN 0.73; SDK 51 → RN 0.74. Pin in `package.json` — mismatched RN/Expo combo breaks Metro resolution silently.
- **Reanimated**: requires `react-native-reanimated/plugin` LAST in `babel.config.js` plugins list; misorder causes runtime worklet failures.

## Testing

- **Unit**: jest + `@testing-library/react-native` (RNTL) — component query API mirrors web RTL. Mock `react-native-reanimated` via the package's `mock.js`.
- **E2E**: Detox (gray-box, runs on simulator/emulator) for happy paths; Maestro (YAML-driven, lighter setup) for smoke flows.
- **Native**: XCTest (iOS) / Espresso (Android) only when touching native modules — otherwise RNTL + Detox is enough.

## Related Skills

- `react` (shared component model, hooks)
- `browser` (JS/Hermes runtime parallels — fetch, URL, AbortController behave nearly identically)
- `nodejs` (Metro runs on Node; CLI tooling shares ESM/CJS pitfalls)
