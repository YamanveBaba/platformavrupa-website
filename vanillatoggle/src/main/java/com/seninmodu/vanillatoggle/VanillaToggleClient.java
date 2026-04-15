package com.seninmodu.vanillatoggle;

import com.mojang.blaze3d.platform.InputConstants;
import com.seninmodu.vanillatoggle.config.VanillaToggleConfig;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import org.lwjgl.glfw.GLFW;

public class VanillaToggleClient implements ClientModInitializer {
	private static final KeyMapping.Category CATEGORY = KeyMapping.Category.register(Identifier.fromNamespaceAndPath("vanillatoggle", "main"));
	private static KeyMapping toggleKey;

	@Override
	public void onInitializeClient() {
		VanillaToggleConfig.load();
		VanillaModeState.setVanillaMode(VanillaToggleConfig.get().startInVanillaMode());

		toggleKey = KeyBindingHelper.registerKeyBinding(new KeyMapping(
				"key.vanillatoggle.toggle",
				InputConstants.Type.KEYSYM,
				GLFW.GLFW_KEY_V,
				CATEGORY
		));

		VanillaToggleHud.register();

		ClientTickEvents.END_CLIENT_TICK.register(client -> {
			while (toggleKey.consumeClick()) {
				VanillaModeState.toggle();
				showFeedback(client);
			}
		});
	}

	private static void showFeedback(Minecraft client) {
		boolean vanilla = VanillaModeState.isVanillaMode();
		Component message = vanilla
				? Component.translatable("vanillatoggle.feedback.vanilla")
				: Component.translatable("vanillatoggle.feedback.modded");

		if (VanillaToggleConfig.get().feedbackUsesActionBar()) {
			client.gui.setOverlayMessage(message, false);
			return;
		}
		if (client.player != null) {
			client.player.displayClientMessage(message, false);
		}
	}
}
