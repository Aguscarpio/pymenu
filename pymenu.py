from typing import Iterable, Callable
import os, sys
import inspect

def clear():
    """Clear the console"""
    os.system('cls' if os.name == 'nt' else 'clear')

# fzf and getch until line 135

def fzf(options: Iterable, msg: str="", reverse: bool=False, limit: int=15,
        choice: int=0):
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
    # TODO Cambiar fuzzyfinder por TheFuzz ??
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



    valid_chars = string.ascii_lowercase+"0123456789"+string.ascii_uppercase+" ,.;:-_´áéíóúñÁÉÍÓÚ"
    substr, ch = "", ""
    # Convert Menu.options to readable option.labels if necessary
    opt_list = []
    pickstringlist = []
    for opt in options:
        # TODO type Option?
        if hasattr(opt,"label"):
            pickstring = ""
            if hasattr(opt,"picked"):
                if opt.picked:
                    pickstring = " [X]"
                else:
                    pickstring = " [ ]"
            opt_list.append(opt.label)
            pickstringlist.append(pickstring)
    pickdict = dict(zip(opt_list,pickstringlist))

    #  choice = 0
    while True:
        candidates = list(ff(substr, opt_list))
        prevch = ch
        clear()
        if reverse:
            print(msg+substr)
        if len(candidates)>limit: # Limit (adapt to screen size)
            candidates = candidates[:limit]
        for cand in candidates:
            if cand==candidates[choice]:
                print(f"\033[92m> {cand+pickdict[cand]}\033[0m") # Green color for chosen option
            else:
                print(cand+pickdict[cand])
        if not reverse:
            print(msg+substr)

        ch = getch()
        if type(ch)!=str and ch not in ['\x1b', '[']: # correct bad encoding
            ch = ch.decode('utf-8')

        if ch=='\r':# Choose option with Enter
            chosen = candidates[choice]
            break
        elif ch=='\t': # Change option with Tab
            choice += 1
            if choice>=len(candidates):
                choice=0 # Ciclic
            continue

        elif ch=='C' and prevch=='[': # Choose option with right key
            chosen = candidates[choice]
            break
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
    # TODO if is Option
    if type(options[0]) in [Menu,Action,Pick]:
        for opt in options:
            if opt.label==chosen:
                opt.choose()
                break
        return

    return choice


# Here the magic begins

class Option:
    """ General class to represent a single option inside a Menu
    """
    def __init__(self, label: str, terminal: bool=True, prev='root'):
        self.label = label
        self.terminal = terminal
        self.prev = prev

    def choose(self):
        if type(self)==Menu:
            self.navigate()
        elif type(self)==Action:
            self.execute()
        elif type(self)==Pick:
            self.pick()

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
        self.picks = []

        # prev attribute of all options setted to Menu
        for opt in options:
            opt.prev = self

    # TODO **kwargs
    def navigate(self, choice=0, limit=25, title="", reverse=False):
        return fzf(self.options, choice=choice, limit=limit, msg=title,
                reverse=reverse)

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
            funcargs = inspect.getfullargspec(func).args
            if len(funcargs)==0:
                func()
            else:
                func(self)

class Pick(Option):
    """
    A class used to create a pickable Option object.

    Picks are inside Menus and can be picked/unpicked (change bw True/False)
    """
    def __init__(self, label: str, picked=False):
        Option.__init__(self, label)
        self.picked = picked
    def pick(self, keep=True):
        self.picked = not(self.picked)
        if self.picked:
            self.prev.picks.append(self.label)
        else:
            self.prev.picks.remove(self.label)

        #  self.prev.navigate(choice=self.prev.options.index(self))
        if keep:
            self.prev.navigate(choice=sorted(self.prev.options, key=lambda x: x.label).index(self))

