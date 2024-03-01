    import pystray
    from PIL import Image

    def setup_tray_icon():
        image = Image.new('RGB', (16, 16), color='red')  # Simple red square
        icon = pystray.Icon("Test Icon", image, title="Test Icon")
        icon.run()

    if __name__ == "__main__":
        setup_tray_icon()
    