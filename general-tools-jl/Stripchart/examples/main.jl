using Stripchart
using Sockets
using Dates

function run()
    # defaults to log path on primary FOXSI GSE computer
    startfolder = abspath(joinpath(homedir(), "Documents", "FOXSI", "GSE", "GSE-FOXSI-4", "logs", "received"))
    candidates = filter(isdir, readdir(startfolder; join=true))
    println(basename(candidates[1]))
    dts = [Dates.DateTime(basename(d), "dd-mm-YYYY_HH-MM-SS") for d in candidates]
    dlatest,klatest = findmax(dts)
    
    logfolder = candidates[klatest]
    println("reading from: ", logfolder)
    run(logfolder)
end

function run(logfolder::AbstractString)
    power_file = abspath(joinpath(logfolder, "housekeeping_pow.log"))
    rtd_file = abspath(joinpath(logfolder, "housekeeping_rtd.log"))
    stripchart_file(power_file, rtd_file)
end

function run(power_file::AbstractString, rtd_file::AbstractString)
    stripchart_file(power_file, rtd_file)
end

function run(ip::IPv4, port::Int; group::String="")
    # udp_listen(ip, port; group)
    sock = udp_setup(ip, port; group=group)
    stripchart(sock)
    # while true
    #     data = recv(sock)
    #     ret = parse_tlm(data; verbose=false, timestyle=:local)
    #     if !isnothing(ret)
    #         println(ret[1], ": ", ret[3])
    #     end 
    #     # if length(data) == Stripchart.frame_size_rtd
    #     #     t,f,T = parse_rtd(data, timestyle=:remote)
    #     #     println(t, ", ", T)
    #     # end
    # end
end