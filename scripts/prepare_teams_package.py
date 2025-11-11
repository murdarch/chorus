"""Helper script to prepare Teams app package."""

import json
import uuid
import sys
from pathlib import Path


def main():
    """Prepare Teams app package with bot IDs."""

    print("🎯 Chorus Teams App Package Preparation")
    print("=" * 60)

    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("   Create .env from .env.example first")
        return 1

    # Read bot IDs from .env
    nous_bot_id = None
    claude_bot_id = None

    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line.startswith("NOUS_BOT_APP_ID="):
                nous_bot_id = line.split("=", 1)[1].strip()
            elif line.startswith("CLAUDE_BOT_APP_ID="):
                claude_bot_id = line.split("=", 1)[1].strip()

    if not nous_bot_id or nous_bot_id.startswith("test_") or nous_bot_id.startswith("your_"):
        print("⚠️  NOUS_BOT_APP_ID not set in .env")
        print("   Set this to your Azure Bot App ID for Nous")
        nous_bot_id = None

    if not claude_bot_id or claude_bot_id.startswith("test_") or claude_bot_id.startswith("your_"):
        print("⚠️  CLAUDE_BOT_APP_ID not set in .env")
        print("   Set this to your Azure Bot App ID for Claude")
        claude_bot_id = None

    # Load manifest template
    manifest_path = Path("teams-app/manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Update manifest
    print("\n📝 Updating manifest.json...")

    # Generate new GUID if needed
    if manifest["id"] == "REPLACE-WITH-NEW-GUID":
        new_guid = str(uuid.uuid4())
        manifest["id"] = new_guid
        print(f"   ✓ Generated new app ID: {new_guid}")
    else:
        print(f"   ✓ Using existing app ID: {manifest['id']}")

    # Update bot IDs
    if nous_bot_id:
        manifest["bots"][0]["botId"] = nous_bot_id
        print(f"   ✓ Set Nous bot ID: {nous_bot_id[:20]}...")
    else:
        print(f"   ⚠️  Nous bot ID still needs to be set")

    if claude_bot_id:
        manifest["bots"][1]["botId"] = claude_bot_id
        print(f"   ✓ Set Claude bot ID: {claude_bot_id[:20]}...")
    else:
        print(f"   ⚠️  Claude bot ID still needs to be set")

    # Save updated manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✅ Updated {manifest_path}")

    # Check for icons
    print("\n🎨 Checking for icon files...")
    color_icon = Path("teams-app/icons/color-icon.png")
    outline_icon = Path("teams-app/icons/outline-icon.png")

    if color_icon.exists():
        print(f"   ✓ Found color-icon.png")
    else:
        print(f"   ❌ Missing color-icon.png (192x192 px)")
        print(f"      Create at: {color_icon}")

    if outline_icon.exists():
        print(f"   ✓ Found outline-icon.png")
    else:
        print(f"   ❌ Missing outline-icon.png (32x32 px)")
        print(f"      Create at: {outline_icon}")

    # Create package if icons exist
    if color_icon.exists() and outline_icon.exists():
        print("\n📦 Creating Teams app package...")

        import zipfile

        zip_path = Path("teams-app/chorus-app.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write("teams-app/manifest.json", "manifest.json")
            zf.write("teams-app/icons/color-icon.png", "icons/color-icon.png")
            zf.write("teams-app/icons/outline-icon.png", "icons/outline-icon.png")

        print(f"   ✅ Created {zip_path}")
        print(f"\n🎉 Ready to upload to Teams!")
        print(f"   1. Open Teams → Apps → Manage your apps")
        print(f"   2. Upload a custom app → Select {zip_path}")

    else:
        print("\n⚠️  Cannot create package - missing icon files")
        print("   Create placeholder icons or use image editing software")

    print("\n" + "=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
