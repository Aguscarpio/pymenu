from typing import Iterable, Callable
import os, sys

def clear():
    """Clear the console"""
    os.system('cls' if os.name == 'nt' else 'clear')

# fzf and getch until line 135

def fzf(options: Iterable, msg: str="", reverse: bool=False):
    """Live FuzzyFinder over an Iterable.

    Parameters
    ----------
    msg : str
        optional string message displayed along the FF itself.

    reverse : bool
        if False, options are printed before msg
        if True, options are printed after msg

    Returns
    -------
    chosen : chosen option

    if options are Menu.options, there is no return, but excecution.
    """
    from fuzzyfinder import fuzzyfinder as ff
    import string

    class _Getch:
        """Gets a single character from standard input.  Does not echo to the
        screen."""
        def __init__(self):
            try:
                self.impl = _GetchWindows()
            except ImportError:
                self.impl = _GetchUnix()

        def __call__(self): return self.impl()


    class _GetchUnix:
        def __init__(self):
            import tty, sys

        def __call__(self):
            import sys, tty, termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch


    class _GetchWindows:
        def __init__(self):
            import msvcrt

        def __call__(self):
            import msvcrt
            return msvcrt.getch()

    getch = _Getch()



    valid_chars = string.ascii_lowercase+"0123456789"+string.ascii_uppercase+" ,.;:-_´áéíóúñ"
    substr, ch = "", ""
    choice = 0
    while True:
        prevch = ch
        clear()
        if reverse:
            print(msg+substr)
        # Convert Menu.options to readable option.labels if necessary
        if type(options[0]) in [Menu,Action]:
            candidates = list(ff(substr, [opt.label for opt in options]))
        else:
            candidates = list(ff(substr, options))
        if len(candidates)>20: # Limit (adapt to screen size)
            candidates = candidates[:20]
        for cand in candidates:
            if cand==candidates[choice]:
                print(f"\033[92m{cand}\033[0m") # Green color for chosen option
            else:
                print(cand)
        if not reverse:
            print(msg+substr)

        ch = getch()
        if ch=='\r':# Choose option with Enter
            chosen = candidates[choice]
            break
        elif ch=='\t': # Change option with Tab
            choice += 1
            if choice>=len(candidates):
                choice=0 # Ciclic
            continue
        elif ch=='B' and prevch=='[': # Navigate Down
            choice += 1
            if choice>=len(candidates):
                choice=0#Cíclico
            continue
        elif ch=='A' and prevch=='[': # Navigate Up
            choice -=1
            if choice==-1:
                choice=len(candidates)-1
            continue
        elif ch=='D' and prevch=='[': # Back menu
            (options[0].prev).back()
            return
        elif ch in valid_chars: # Simple append
            choice = 0
            substr += ch
            continue
        elif ch in ['\x1b', '[']: # Prepare for composed key
            continue
        else: # Delete last character
            substr = substr[:-1]
    clear()

    # navigate Menu or excecute Action if options are Menu.options
    if type(options[0]) in [Menu,Action]:
        for opt in options:
            if opt.label==chosen:
                opt.choose()
                break
        return

    return chosen


# Here the magic begins

class Option:
    """General class to represent a single option inside a Menu"""
    def __init__(self, label: str, terminal: bool=True, prev='root'):
        self.label = label
        self.terminal = terminal
        self.prev = prev

    def choose(self):
        if type(self)==Menu:
            self.navigate()
        if type(self)==Action:
            self.execute()

    def back(self): # Go back to previous Menu
        if self.prev=='root': # if root -> exit program
            clear()
            sys.exit()
        else:
            (self.prev).navigate()


class Menu(Option):
    """
    A class used to create a Menu Option object.

    Every Menu should have a previous Menu due to the tree nature. In case of
    main Menu, prev="root".
    """

    def __init__(self, label: str, options: Iterable):
        Option.__init__(self, label, terminal=False)
        self.options = list(options)

        # prev attribute of all options setted to Menu
        for opt in options:
            opt.prev = self

    def navigate(self):
        fzf(self.options)

    def tree_view(self, tabbing: int=0):
        """Method to see nested tree structure of Menus"""
        for opt in self.options:
            if type(opt)==Menu:
                print('\t'*tabbing+opt.label)
                opt.tree_view(tabbing+1)
            elif type(opt)==Action:
                print('\t'*tabbing+opt.label)



class Action(Option):
    """
    A class used to create a callable Option object.

    Actions are inside Menus and can be excecuted (trigger their functions)
    """
    def __init__(self, label: str, *funcs: Callable):
        Option.__init__(self, label)
        self.funcs = funcs
    def execute(self):
        for func in self.funcs:
            func()
