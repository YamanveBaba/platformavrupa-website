package com.seninmodu.vanillatoggle;

import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;

/**
 * Demo feature: when non-vanilla (mod features on), show a small indicator that the mod is active.
 */
public final class VanillaToggleHud {
	private static final Identifier ELEMENT_ID = Identifier.fromNamespaceAndPath("vanillatoggle", "mod_indicator");

	private VanillaToggleHud() {
	}

	public static void register() {
		HudElementRegistry.addLast(ELEMENT_ID, VanillaToggleHud::render);
	}

	private static void render(GuiGraphics graphics, DeltaTracker tickCounter) {
		if (VanillaModeState.isVanillaMode()) {
			return;
		}
		Minecraft client = Minecraft.getInstance();
		Component label = Component.translatable("vanillatoggle.hud.mod_active");
		int x = 6;
		int y = 6;
		int color = 0xFF55FF55;
		graphics.drawTextWithShadow(client.font, label, x, y, color);
	}
}
