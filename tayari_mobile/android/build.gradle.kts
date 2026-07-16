allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)

    afterEvaluate {
        project.extensions.findByName("android")?.let { android ->
            try {
                android.javaClass.getMethod("setCompileSdk", Int::class.javaPrimitiveType).invoke(android, 36)
            } catch (e: Exception) {
                try {
                    android.javaClass.getMethod("setCompileSdkVersion", Int::class.javaPrimitiveType).invoke(android, 36)
                } catch (e2: Exception) { }
            }
            try {
                val namespace = android.javaClass.getMethod("getNamespace").invoke(android) as? String
                if (namespace.isNullOrEmpty()) {
                    val groupStr = project.group.toString()
                    val fallback = if (groupStr.isNotEmpty() && groupStr != "unspecified") {
                        groupStr.replace("[^a-zA-Z0-9_.]".toRegex(), "_")
                    } else {
                        "dev.flutter.plugin.${project.name.replace("[^a-zA-Z0-9_.]".toRegex(), "_")}"
                    }
                    android.javaClass.getMethod("setNamespace", String::class.java).invoke(android, fallback)
                }
            } catch (e: Exception) { }
        }
    }
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
