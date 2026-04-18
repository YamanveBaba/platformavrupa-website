package com.seninmodu.vanillatoggle.config;

import me.shedaniel.clothconfig2.api.ConfigBuilder;
import me.shedaniel.clothconfig2.api.ConfigCategory;
import me.shedaniel.clothconfig2.api.ConfigEntryBuilder;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public final class VanillaToggleConfigScreen {
	private VanillaToggleConfigScreen() {
	}

	public static Screen create(Screen parent) {
		VanillaToggleConfig c = VanillaToggleConfig.get();
		ConfigBuilder builder = ConfigBuilder.create()
				.setParentScreen(parent)
				.setTitle(Component.translatable("vanillatoggle.config.title"))
				.setSavingRunnable(VanillaToggleConfig::save);

		ConfigCategory general = builder.getOrCreateCategory(Component.translatable("vanillatoggle.config.category.general"));
		general.addEntry(ConfigEntryBuilder.create()
				.startBooleanToggle(Component.translatable("vanillatoggle.config.start_vanilla"), c.startInVanillaMode())
				.setDefaultValue(false)
				.setTooltip(Component.translatable("vanillatoggle.config.start_vanilla.tooltip"))
				.setSaveConsumer(c::setStartInVanillaMode)
				.build());
		general.addEntry(ConfigEntryBuilder.create()
				.startBooleanToggle(Component.translatable("vanillatoggle.config.action_bar"), c.feedbackUsesActionBar())
				.setDefaultValue(true)
				.setTooltip(Component.translatable("vanillatoggle.config.action_bar.tooltip"))
				.setSaveConsumer(c::setFeedbackUsesActionBar)
				.build());

		return builder.build();
	}
}
