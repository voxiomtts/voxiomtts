from gui import VoxiomTTSApp
import multiprocessing
import sys

def main():
    try:
        multiprocessing.freeze_support()
        print("Starting application...")
        app = VoxiomTTSApp()
        app.mainloop()
    except Exception as e:
        print(f"Application failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
