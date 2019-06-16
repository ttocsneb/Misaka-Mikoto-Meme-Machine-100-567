from dice_roller import serve

# __main__.py is run when the package is run directly: python dm_assist

from sys import argv

serve(
    debug=True if '--debug' in argv else False,
    test=True if '--upgrade' in argv else False
)
