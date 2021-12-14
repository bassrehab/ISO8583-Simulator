import logging

# This class could be imported from a utility module
class LogMixin(object):
    @property
    def logger(self):
        name = '.'.join([__name__, self.__class__.__name__])
        return logging.getLogger(name)


# This class is just there to show that you can use a mixin like LogMixin
class Base(object):
    pass

# This could be in a module separate from B
class A(Base, LogMixin):
    def __init__(self):
        # Example of logging from a method in one of your classes
        self.logger.debug('Hello from A')

# This could be in a module separate from A
class B(Base, LogMixin):
    def __init__(self):
        # Another example of logging from a method in one of your classes
        self.logger.debug('Hello from B')

def main():
    # Do some work to exercise logging
    a = A()
    b = B()
    with open('myapp.log') as f:
        print('Log file contents:')
        print(f.read())

if __name__ == '__main__':
    # Configure only in your main program clause
    logging.basicConfig(level=logging.DEBUG,
                        filename='myapp.log', filemode='w',
                        format='%(name)s %(levelname)s %(message)s')
    main()