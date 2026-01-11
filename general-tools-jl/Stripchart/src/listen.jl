using Dates

function parse_rtd(frame::Vector{UInt8}; timestyle=:local)
    @assert(length(frame) == frame_size_rtd)
    
    timestamp = Nothing
    if timestyle == :remote
        timestamp = unix2datetime(reinterpret(UInt32, reverse(frame[3:6]))[1])
    elseif timestyle == :local
        timestamp = Dates.now()
    end
    
    flags = Vector{UInt8}(undef, 9)
    temps = Vector{Float32}(undef, 9)
    
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
    
    return timestamp, flags, temps
end

function udp_setup(ip::IPv4, port::Int; group::IPv4="")
    socket = Sockets.UDPSocket()
     
    bound = bind(socket, ip, port; reuseaddr=true)
    if !bound
        throw("Failed to bind to socket")
    end
    if group != ""
        join_multicast_group(socket, group)
        println("joined multicast group")
    end
    
    return socket
end