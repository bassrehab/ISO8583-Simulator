if __name__ == "__main__":
    print('*********************************************************')
    print('*        ISO 8583 Simulator                              *')
    print('*********************************************************\n')


    # Start Sim server.
    from classes.server.server import SimulatorServer
    SimulatorServer()
