def increase(colour, increments):
    """Take a colour and increase each channel by the increments given in the list"""
    colour_values = [int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:], 16)]
    output = [min(255, colour_values[0] + increments[0]), min(255, colour_values[1] + increments[1]), min(255, colour_values[2] + increments[2])]
    output = [max(0, output[0]), max(0, output[1]), max(0, output[2])]
    return '#{}{}{}'.format(hex(output[0])[2:], hex(output[1])[2:], hex(output[2])[2:])

def multiply(colour, multipliers):
    """Take a colour and multiply each channel by the multipliers given in the list"""
    colour_values = [int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:], 16)]
    output = [min(255, colour_values[0] * multipliers[0]), min(255, colour_values[1] * multipliers[1]), min(255, colour_values[2] * multipliers[2])]
    output = [max(0, output[0]), max(0, output[1]), max(0, output[2])]
    return '#{}{}{}'.format(hex(output[0])[2:], hex(output[1])[2:], hex(output[2])[2:])