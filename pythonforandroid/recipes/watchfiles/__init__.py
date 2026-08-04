from pythonforandroid.recipe import RustCompiledComponentsRecipe


class WatchfilesRecipe(RustCompiledComponentsRecipe):
    version = "1.1.1"
    url = (
        "https://github.com/samuelcolvin/watchfiles/archive/refs/tags/v{version}.tar.gz"
    )

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)
        env["ANDROID_API_LEVEL"] = str(self.ctx.ndk_api)
        return env


recipe = WatchfilesRecipe()
