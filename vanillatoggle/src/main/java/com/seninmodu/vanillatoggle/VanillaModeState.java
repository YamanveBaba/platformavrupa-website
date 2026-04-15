package com.seninmodu.vanillatoggle;

/**
 * Single source of truth for "vanilla mode" (this mod's features off) vs mod features on.
 * Read from the client thread only.
 */
public final class VanillaModeState {
	private static boolean vanillaMode;

	private VanillaModeState() {
	}

	public static boolean isVanillaMode() {
		return vanillaMode;
	}

	public static void setVanillaMode(boolean vanilla) {
		vanillaMode = vanilla;
	}

	public static void toggle() {
		vanillaMode = !vanillaMode;
	}
}
