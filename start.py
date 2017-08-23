if __name__ == "__main__":
    print('*********************************************************')
    print('*        IS) 8583 Simulator                              *')
    print('*********************************************************\n')


    # Start UTU-Sim server.
    from classes.server.server import SimulatorServer
    SimulatorServer()