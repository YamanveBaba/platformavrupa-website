package com.seninmodu.vanillatoggle.integration;

import com.seninmodu.vanillatoggle.config.VanillaToggleConfigScreen;
import com.terraformersmc.modmenu.api.ConfigScreenFactory;
import com.terraformersmc.modmenu.api.ModMenuApi;

public final class VanillaToggleModMenu implements ModMenuApi {
	@Override
	public ConfigScreenFactory<?> getModConfigScreenFactory() {
		return VanillaToggleConfigScreen::create;
	}
}
