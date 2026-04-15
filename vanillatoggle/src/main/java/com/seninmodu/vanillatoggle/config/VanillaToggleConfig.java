package com.seninmodu.vanillatoggle.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class VanillaToggleConfig {
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
	private static final Path PATH = FabricLoader.getInstance().getConfigDir().resolve("vanillatoggle.json");

	private boolean startInVanillaMode;
	private boolean feedbackUsesActionBar;

	public VanillaToggleConfig() {
		this.startInVanillaMode = false;
		this.feedbackUsesActionBar = true;
	}

	public boolean startInVanillaMode() {
		return startInVanillaMode;
	}

	public void setStartInVanillaMode(boolean startInVanillaMode) {
		this.startInVanillaMode = startInVanillaMode;
	}

	public boolean feedbackUsesActionBar() {
		return feedbackUsesActionBar;
	}

	public void setFeedbackUsesActionBar(boolean feedbackUsesActionBar) {
		this.feedbackUsesActionBar = feedbackUsesActionBar;
	}

	private static VanillaToggleConfig instance = new VanillaToggleConfig();

	public static VanillaToggleConfig get() {
		return instance;
	}

	public static void load() {
		if (!Files.isRegularFile(PATH)) {
			instance = new VanillaToggleConfig();
			save();
			return;
		}
		try {
			String json = Files.readString(PATH, StandardCharsets.UTF_8);
			VanillaToggleConfig loaded = GSON.fromJson(json, VanillaToggleConfig.class);
			instance = loaded != null ? loaded : new VanillaToggleConfig();
		} catch (IOException e) {
			instance = new VanillaToggleConfig();
		}
	}

	public static void save() {
		try {
			Files.createDirectories(PATH.getParent());
			Files.writeString(PATH, GSON.toJson(instance), StandardCharsets.UTF_8);
		} catch (IOException ignored) {
		}
	}
}
