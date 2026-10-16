"""Desktop entry point, with explicit diagnostics capture for windowed CI builds."""
import sys
if '--diagnostic-output' in sys.argv:
    index = sys.argv.index('--diagnostic-output')
    destination = sys.argv[index + 1]
    del sys.argv[index:index + 2]
    # Only opt-in test output; never capture normal document processing.
    sys.stdout = sys.stderr = open(destination, 'w', encoding='utf-8', buffering=1)
from nomi.app import main
if __name__ == '__main__':
    main()
