"""Generate the small, relocatable Xcode app project using only Python's standard library.

The app has a local Swift package core and a pinned KeyboardShortcuts dependency.
Xcode packages localized SwiftPM resource bundles in the correct signed app location.
"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
project = root / "OverAI.xcodeproj"
project.mkdir(exist_ok=True)
objects = {}
release = json.loads((root / "Release.json").read_text())


def ident(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24].upper()


def ref(name):
    return ident(name)


def add(key, isa, **fields):
    objects[ident(key)] = dict(isa=isa, **fields)
    return ident(key)


def encode(value, depth=0):
    if isinstance(value, dict):
        return "{\n" + "\n".join("\t" * (depth + 1) + str(k) + " = " + encode(v, depth + 1) + ";" for k, v in value.items()) + "\n" + "\t" * depth + "}"
    if isinstance(value, list):
        return "(\n" + "\n".join("\t" * (depth + 1) + encode(v, depth + 1) + "," for v in value) + "\n" + "\t" * depth + ")"
    return json.dumps(str(value))


source_refs = []
source_builds = []
for source in sorted((root / "Sources/OverAI").glob("*.swift")):
    name = source.name
    source_refs.append(add("file:" + name, "PBXFileReference", lastKnownFileType="sourcecode.swift", path=name, sourceTree="<group>"))
    source_builds.append(add("build:" + name, "PBXBuildFile", fileRef=ref("file:" + name)))

add("sources", "PBXGroup", children=source_refs, path="Sources/OverAI", sourceTree="<group>")
add("plist", "PBXFileReference", lastKnownFileType="text.plist.xml", path="Info.plist", sourceTree="<group>")
add("notices", "PBXFileReference", lastKnownFileType="text", path="Sources/OverAI/Resources/ThirdPartyNotices.txt", sourceTree="<group>")
add("icon", "PBXFileReference", lastKnownFileType="image.icns", path="Sources/OverAI/Resources/icon.icns", sourceTree="<group>")
add("provider-icons", "PBXFileReference", lastKnownFileType="folder", path="Sources/OverAI/Resources/ProviderIcons", sourceTree="<group>")
add("provider-icons-build", "PBXBuildFile", fileRef=ref("provider-icons"))
add("notices-build", "PBXBuildFile", fileRef=ref("notices"))
add("icon-build", "PBXBuildFile", fileRef=ref("icon"))
add("product", "PBXFileReference", explicitFileType="wrapper.application", includeInIndex="0", path="OverAI.app", sourceTree="BUILT_PRODUCTS_DIR")
add("products", "PBXGroup", children=[ref("product")], name="Products", sourceTree="<group>")
add("main", "PBXGroup", children=[ref("sources"), ref("plist"), ref("notices"), ref("icon"), ref("provider-icons"), ref("products")], sourceTree="<group>")
add("keyboard-package", "XCRemoteSwiftPackageReference", repositoryURL="https://github.com/sindresorhus/KeyboardShortcuts", requirement={"kind": "exactVersion", "version": "3.1.0"})
add("core-package", "XCLocalSwiftPackageReference", relativePath=".")
add("keyboard-product", "XCSwiftPackageProductDependency", package=ref("keyboard-package"), productName="KeyboardShortcuts")
add("core-product", "XCSwiftPackageProductDependency", productName="OverAICore", package=ref("core-package"))
add("keyboard-link", "PBXBuildFile", productRef=ref("keyboard-product"))
add("core-link", "PBXBuildFile", productRef=ref("core-product"))
add("sources-phase", "PBXSourcesBuildPhase", buildActionMask="2147483647", files=source_builds, runOnlyForDeploymentPostprocessing="0")
add("frameworks-phase", "PBXFrameworksBuildPhase", buildActionMask="2147483647", files=[ref("keyboard-link"), ref("core-link")], runOnlyForDeploymentPostprocessing="0")
add("resources-phase", "PBXResourcesBuildPhase", buildActionMask="2147483647", files=[ref("notices-build"), ref("icon-build"), ref("provider-icons-build")], runOnlyForDeploymentPostprocessing="0")

for config in ["Debug", "Release"]:
    add("project-" + config, "XCBuildConfiguration", name=config, buildSettings={
        "SDKROOT": "macosx", "MACOSX_DEPLOYMENT_TARGET": "14.0", "ARCHS": "arm64", "SWIFT_VERSION": "5.0",
        "CLANG_ENABLE_MODULES": "YES", "SWIFT_OPTIMIZATION_LEVEL": "-Onone" if config == "Debug" else "-O",
        "DEBUG_INFORMATION_FORMAT": "dwarf" if config == "Debug" else "dwarf-with-dsym",
    })
    add("app-" + config, "XCBuildConfiguration", name=config, buildSettings={
        "PRODUCT_NAME": "OverAI", "PRODUCT_MODULE_NAME": "OverAIApp", "PRODUCT_BUNDLE_IDENTIFIER": "com.overai.native",
        "INFOPLIST_FILE": "Info.plist", "GENERATE_INFOPLIST_FILE": "NO", "MARKETING_VERSION": release["version"],
        "CURRENT_PROJECT_VERSION": release["build"], "CODE_SIGN_STYLE": "Manual", "CODE_SIGN_IDENTITY": "-",
        "CODE_SIGN_ENTITLEMENTS": "OverAI.entitlements",
        "CODE_SIGN_INJECT_BASE_ENTITLEMENTS": "YES" if config == "Debug" else "NO",
        "ENABLE_HARDENED_RUNTIME": "YES", "ENABLE_APP_SANDBOX": "NO", "COMBINE_HIDPI_IMAGES": "YES",
        "LD_RUNPATH_SEARCH_PATHS": ["$(inherited)", "@executable_path/../Frameworks"],
    })
add("project-configs", "XCConfigurationList", buildConfigurations=[ref("project-Debug"), ref("project-Release")], defaultConfigurationIsVisible="0", defaultConfigurationName="Release")
add("app-configs", "XCConfigurationList", buildConfigurations=[ref("app-Debug"), ref("app-Release")], defaultConfigurationIsVisible="0", defaultConfigurationName="Release")
add("app", "PBXNativeTarget", name="OverAI", productName="OverAI", productReference=ref("product"),
    productType="com.apple.product-type.application", buildConfigurationList=ref("app-configs"),
    buildPhases=[ref("sources-phase"), ref("frameworks-phase"), ref("resources-phase")], buildRules=[], dependencies=[],
    packageProductDependencies=[ref("keyboard-product"), ref("core-product")])
add("project", "PBXProject", attributes={"LastUpgradeCheck": "2630"}, buildConfigurationList=ref("project-configs"),
    compatibilityVersion="Xcode 14.0", developmentRegion="en", hasScannedForEncodings="0", knownRegions=["en", "Base"],
    mainGroup=ref("main"), productRefGroup=ref("products"), projectDirPath="", projectRoot="", targets=[ref("app")],
    packageReferences=[ref("keyboard-package"), ref("core-package")])

payload = {"archiveVersion": "1", "classes": {}, "objectVersion": "56", "objects": objects, "rootObject": ref("project")}
(project / "project.pbxproj").write_text("// !$*UTF8*$!\n" + encode(payload) + "\n")
schemes = project / "xcshareddata/xcschemes"
schemes.mkdir(parents=True, exist_ok=True)
buildable = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{ref("app")}" BuildableName="OverAI.app" BlueprintName="OverAI" ReferencedContainer="container:OverAI.xcodeproj"/>'
(schemes / "OverAI.xcscheme").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="2630" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{buildable}</BuildActionEntry></BuildActionEntries></BuildAction>
  <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{buildable}</BuildableProductRunnable></LaunchAction>
  <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{buildable}</BuildableProductRunnable></ProfileAction>
  <AnalyzeAction buildConfiguration="Debug"/>
  <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>
''')
print("Generated", project)
