# Vanilla Toggle (Fabric, Minecraft 1.21.11)

Client-only mod: press **V** (default) to toggle between **vanilla mode** (this mod’s optional behaviors off) and **mod mode** (behaviors on). Use `VanillaModeState.isVanillaMode()` in your own code to gate features.

## Run from source

Requirements: **JDK 21**, network for Gradle/Minecraft deps.

```bash
cd vanillatoggle
./gradlew runClient
```

On Windows: `gradlew.bat runClient`

## Build

```bash
./gradlew build
```

Output: `build/libs/vanillatoggle-1.0.0.jar` (version from `gradle.properties`).

## Modrinth / CurseForge

- **Loader:** Fabric  
- **Minecraft:** 1.21.11  
- **Dependencies:** Fabric API, [Mod Menu](https://modrinth.com/mod/modmenu), [Cloth Config](https://modrinth.com/mod/cloth-config) (for the settings screen and JSON config under `config/vanillatoggle.json`)  
- **Side:** client only (`environment: client` in `fabric.mod.json`)

Short description for listings: *One key toggles client-side “vanilla vs mod” mode for this mod’s features; includes HUD indicator and Mod Menu config.*

## License

MIT — see [LICENSE](LICENSE).
