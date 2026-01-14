using Dates

@enum System begin 
    housekeeping=0x02
end

@enum PacketType begin 
    pow=0x11
    rtd=0x12
end

function parse_tlm(packet::Vector{UInt8}; verbose::Bool=false, timestyle=:local)
    if length(packet) < 9
        return nothing
    end
    
    if packet[1] == Int(housekeeping::System)    # housekeeping system
        if packet[6] == Int(pow::PacketType)     # power data
            return parse_pow(packet[9:end]; timestyle=timestyle)
        elseif packet[6] == Int(rtd::PacketType) # rtd data
            return parse_rtd(packet[9:end]; timestyle=timestyle)
        else
            if verbose
                println("got unparseable hk data type 0x"*string(packet[6], base=16))
            end
        end
    else
        if verbose
            println("got unparseable system type 0x"*string(packet[1], base=16))
        end
    end
    return nothing
end

function parse_time(frame::Vector{UInt8}; timestyle=:local)
    timestamp = nothing
    if timestyle == :remote
        timestamp = unix2datetime(reinterpret(UInt32, reverse(frame[3:6]))[1])
    elseif timestyle == :local
        timestamp = Dates.now()
    end
    
    return timestamp
end

function parse_pow(frame::Vector{UInt8}; timestyle=:local)
    @assert(length(frame) == frame_size_pow)
    
    timestamp = parse_time(frame; timestyle=timestyle)
    
    pframe = frame[7:end]
    
    # channels_raw = [int.from_bytes(data[i:i+2],"big") for i in range(6,len(data),2)]
    
    # # measure the 5 V channel, use to bootstrap other measurements.
    # raw_5v_src = int.from_bytes(data[12:14], "big", signed=False)
    
    raw_5v_src = reinterpret(UInt16, [pframe[8]; pframe[7]])[1]
    channel_5v = raw_5v_src >> 12
    
    @assert(channel_5v == 0x03)
    
    ref_5v = 5.0        # [V] reference input voltage for ADC scale
    current_gain = 0.2  # [V/A] current-to-voltage gain for Hall-effect sensors
    
    # # note that last measured on-board, as-built value was 5.36 V for 5 V supply. This 
    # # matches nicely with a coefficient of 1.68.
    divider_coefficients = [9.2, 2.0, 4.0, 1.68]
    measured_5v = divider_coefficients[4] * ref_5v * (raw_5v_src & 0x0fff) / 0x0fff
    
    voltages = Vector{Float32}(undef, 4)
    currents = Vector{Float32}(undef, 12)

    voltagek = 1
    currentk = 1
    for k in 1:16
        val = reinterpret(UInt16, [pframe[2*k]; pframe[2*k - 1]])[1]
        ch = val >> 12
        ratiometric = ref_5v * (val & 0x0fff) / 0x0fff
        if ch < 4
            if ch == 3
                voltages[voltagek] = measured_5v
            else
                voltages[voltagek] = divider_coefficients[voltagek]*ratiometric
            end
            voltagek += 1
        else
            currents[currentk] = (ratiometric - measured_5v/2) / current_gain
            currentk += 1
        end
    end
    return timestamp, [voltages; currents]
end

function parse_rtd(frame::Vector{UInt8}; timestyle=:local)
    @assert(length(frame) == frame_size_rtd)
    
    timestamp = parse_time(frame; timestyle=timestyle)
    
    flags = Vector{UInt8}(undef, 9)
    temps = Vector{Float32}(undef, 9)
    
    chip = frame[1]
    
    init_k = 7
    for k in 0:8
        this_index = init_k + k*4
        this_flag = frame[this_index]
        this_raw = frame[this_index + 1:this_index + 3]
        temp_raw = reinterpret(UInt32, reverse([0x00;this_raw]))[1]
        if (temp_raw & (1 << 23)) > 0
            temp_raw = (~temp_raw & 0xffffff)
            temp_raw = -temp_raw + 1
        end
        this_temp = temp_raw / 1024
        
        flags[k+1] = this_flag
        temps[k+1] = this_temp
    end
    
    nank = findall(flags .!= 1)
    temps[nank] .= NaN
    
    return timestamp, flags, temps, chip
end

function udp_setup(ip::IPv4, port::Int; group::String="")
    socket = Sockets.UDPSocket()
     
    bound = bind(socket, ip, port; reuseaddr=true)
    if !bound
        throw("Failed to bind to socket")
    end
    if group != ""
        println("found multicast")
        join_multicast_group(socket, getaddrinfo(group))
        println("joined multicast group")
    end
    
    return socket
end