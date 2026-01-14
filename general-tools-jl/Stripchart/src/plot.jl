using Dates
using GLMakie

mutable struct Printer
    axis::GLMakie.Axis
    data::Vector{Observable{Vector{<:Real}}} 
    times::Observable{Vector{Dates.DateTime}}
    length::Int
end

Printer(ax::GLMakie.Axis; length::Int=100, width=1) = Printer(
    ax,
    [Observable(zeros(Float32, length)) for k in 1:width],
    Observable(fill(Dates.now(), length)),
    length
)

function push!(p::Printer, time::Dates.DateTime, val::Vector{<:Real})
    
    p.times[] = circshift(p.times[], 1)
    p.times[][1] = time
    GLMakie.notify(p.times)
    
    for k in 1:length(p.data)
        p.data[k][] = circshift(p.data[k][], 1)
        p.data[k][][1] = val[k]
        GLMakie.notify(p.data[k])
    end
    
end

rtd_lookup_cold = Dict(
    "type" => 0x12,
    "chip" => 0x01,
    "indices" => 5:9,
    "labels" => ["focal position 5",
                "focal position 4",
                "focal position 3",
                "focal position 2",
                "ln2 inlet"]
)
rtd_lookup_warm = Dict(
    "type" => 0x12,
    "chip" => 0x01,
    "indices" => 1:4,
    "labels" => ["timepix",
                "saas camera",
                "formatter pi",
                "5.5 V regulator"]
)
rtd_lookup_opt = Dict(
    "type" => 0x12,
    "chip" => 0x02,
    "indices" => 1:9,
    "labels" => ["optic plate",
                "position 6 front",
                "position 6 plate",
                "position 2 plate",
                "position 4 front",
                "position 4 plate",
                "position 0 collimator",
                "position 0 front",
                "position 0 plate"]
)
pow_lookup_curr = Dict(
    "type" => 0x11,
    "chip" => 0x01,
    "indices" => 5:16,
    "labels" => ["regulator I",
                "SAAS camera I",
                "SAAS SBC I",
                "Timepix FPGA I",
                "Timepix SBC I",
                "CdTe DE I",
                "CdTe 1 I",
                "CdTe 5 I",
                "CdTe 3 I",
                "CdTe 4 I",
                "CMOS 1 I",
                "CMOS 3 I"]
)
pow_lookup_volt = Dict(
    "type" => 0x11,
    "chip" => 0x01,
    "indices" => 1:4,
    "labels" => ["28 V in",
                 "5.5 V",
                 "12 V",
                 "5 V"]
)

function stripchart(socket::Sockets.UDPSocket)
    
    
    bufflen = 500
    
    GLMakie.activate!(title="FOXSI housekeeping")
    fig = GLMakie.Figure(size=(1200,800))
    grid = GLMakie.GridLayout(fig[1,1])
    
    display(fig)
    
    # create all axes, buffers.
    cold_ax =       GLMakie.Axis(grid[1,1], title="Cold focal plane\ntemperatures [ºC]")
    cold_flag_ax =  GLMakie.Axis(grid[1,2], xticks=[0,5,9])
    warm_ax =       GLMakie.Axis(grid[1,3], title="Warm detector-end\ntemperatures [ºC]")
    warm_flag_ax =  GLMakie.Axis(grid[1,4], xticks=[0,5,9])
    opt_ax =        GLMakie.Axis(grid[1,5], title="Optics-end\ntemperatures [ºC]")
    opt_flag_ax =   GLMakie.Axis(grid[1,6], xticks=[0,5,9])
    current_ax =    GLMakie.Axis(grid[1,7], title="Current [A]")
    voltage_ax =    GLMakie.Axis(grid[1,8], title="Voltage [V]")
    
    all_ax = [cold_ax, cold_flag_ax, warm_ax, warm_flag_ax, opt_ax, opt_flag_ax, current_ax, voltage_ax]
    
    do_vdiff = GLMakie.Button(grid[3,8], tellwidth=false, label="Differential voltage")
    do_rescale = GLMakie.Button(grid[3,1], tellwidth=false, label="Autoscale")
    do_legend = GLMakie.Toggle(grid[3,2], tellwidth=false, active=true)
    toggle_lab = GLMakie.Label(grid[3,3], "Show legends", tellwidth=false, justification=:left, halign=:left)
    
    rowsize!(grid, 2, Relative(0/3))
    
    colsize!(grid, 1, Relative(1/6))
    colsize!(grid, 3, Relative(1/6))
    colsize!(grid, 5, Relative(1/6))
    colsize!(grid, 7, Relative(1/6))
    colsize!(grid, 8, Relative(1/6))
    colsize!(grid, 2, Relative(1/18))
    colsize!(grid, 4, Relative(1/18))
    colsize!(grid, 6, Relative(1/18))

    cold_plot = Printer(cold_ax, length=bufflen, width=length(rtd_lookup_cold["indices"]))
    [lines!(cold_plot.axis, cold_plot.data[k], cold_plot.times, label=rtd_lookup_cold["labels"][k]) for k in 1:length(rtd_lookup_cold["indices"])]
    cold_flag_plot = Printer(cold_flag_ax, length=bufflen, width=1)
    lines!(cold_flag_plot.axis, cold_flag_plot.data[1], cold_flag_plot.times, color=:black)
    
    warm_plot = Printer(warm_ax, length=bufflen, width=length(rtd_lookup_warm["indices"]))
    [lines!(warm_plot.axis, warm_plot.data[k], warm_plot.times, label=rtd_lookup_warm["labels"][k]) for k in 1:length(rtd_lookup_warm["indices"])]
    warm_flag_plot = Printer(warm_flag_ax, length=bufflen, width=1)
    lines!(warm_flag_plot.axis, warm_flag_plot.data[1], warm_flag_plot.times, color=:black)
    
    opt_plot = Printer(opt_ax, length=bufflen, width=length(rtd_lookup_opt["indices"]))
    [lines!(opt_plot.axis, opt_plot.data[k], opt_plot.times, label=rtd_lookup_opt["labels"][k]) for k in 1:length(rtd_lookup_opt["indices"])]
    opt_flag_plot = Printer(opt_flag_ax, length=bufflen, width=1)
    lines!(opt_flag_plot.axis, opt_flag_plot.data[1], opt_flag_plot.times, color=:black)
    
    curr_plot = Printer(current_ax, length=bufflen, width=length(pow_lookup_curr["indices"]))
    [lines!(curr_plot.axis, curr_plot.data[k], curr_plot.times, label=pow_lookup_curr["labels"][k]) for k in 1:length(pow_lookup_curr["indices"])]
    volt_plot = Printer(voltage_ax, length=bufflen, width=length(pow_lookup_volt["indices"]))
    [lines!(volt_plot.axis, volt_plot.data[k], volt_plot.times, label=pow_lookup_volt["labels"][k]) for k in 1:length(pow_lookup_volt["indices"])]
    
    linkyaxes!(all_ax[1], all_ax[2:end]...)
    [hideydecorations!(all_ax[k]) for k in 2:length(all_ax)]
    [all_ax[k].ygridvisible = true for k in 1:length(all_ax)]
    [all_ax[k].xgridvisible = true for k in 1:length(all_ax)]
    
    [xlims!(all_ax[k], 0, 9) for k in [2, 4, 6]]
    
    # see if these do indeed update after adding plot data
    framevisible = true
    # cold_leg = GLMakie.Legend(grid[2,1], cold_ax, "",   labelsize=10.0, framevisible=framevisible, valign=:top)
    # warm_leg = GLMakie.Legend(grid[2,3], warm_ax, "",   labelsize=10.0, framevisible=framevisible, valign=:top)
    # opt_leg = GLMakie.Legend(grid[2,5], opt_ax, "",     labelsize=10.0, framevisible=framevisible, valign=:top)
    # curr_leg = GLMakie.Legend(grid[2,7], current_ax, "",labelsize=10.0, framevisible=framevisible, valign=:top)
    # volt_leg = GLMakie.Legend(grid[2,8], voltage_ax, "",labelsize=10.0, framevisible=framevisible, valign=:top)
    cold_leg = axislegend(cold_ax,    halign=:left, valign=:bottom, labelsize=10.0, framevisible=framevisible)
    warm_leg = axislegend(warm_ax,    halign=:left, valign=:bottom, labelsize=10.0, framevisible=framevisible)
    opt_leg = axislegend(opt_ax,      halign=:left, valign=:bottom, labelsize=10.0, framevisible=framevisible)
    curr_leg = axislegend(current_ax, halign=:left, valign=:bottom, labelsize=10.0, framevisible=framevisible)
    volt_leg = axislegend(voltage_ax, halign=:left, valign=:bottom, labelsize=10.0, framevisible=framevisible)
    
    all_legs = [cold_leg, warm_leg, opt_leg, curr_leg, volt_leg]
    
    GLMakie.on(do_rescale.clicks) do click_count
        for k in 1:length(all_ax)
            GLMakie.autolimits!(all_ax[k])
        end
    end
    
    GLMakie.on(do_legend.active) do active
        if active
            for leg in all_legs
                leg.labelsize = 10.0
                leg.patchsize = (20,20)
                leg.framevisible = true
            end
        else
            for leg in all_legs
                leg.labelsize = 0
                leg.patchsize = (0,0)
                leg.framevisible = false
            end
        end
    end
    
    while true
        try
            data = recv(socket)
            ret = parse_tlm(data; verbose=false, timestyle=:local)
            if !isnothing(ret)
                if data[1] == 0x02 && data[6] == 0x12 # rtd
                    time, flags, temps, chip = ret
                    if chip == rtd_lookup_cold["chip"]
                        push!(cold_plot, time, temps[rtd_lookup_cold["indices"]])
                        push!(warm_plot, time, temps[rtd_lookup_warm["indices"]])
                        
                        cold_flag = sum(flags[rtd_lookup_cold["indices"]] .!= 1)
                        warm_flag = sum(flags[rtd_lookup_warm["indices"]] .!= 1)
                        push!(cold_flag_plot, time, [cold_flag])
                        push!(warm_flag_plot, time, [warm_flag])
                        
                    elseif chip == rtd_lookup_opt["chip"]
                        push!(opt_plot, time, temps[rtd_lookup_opt["indices"]])
                        opt_flag = sum(flags[rtd_lookup_opt["indices"]] .!= 1)
                        push!(opt_flag_plot, time, [opt_flag])
                        
                    else
                        # error
                    end
                elseif data[1] == 0x02 && data[6] == 0x11 # pow
                    time, values = ret
                    push!(curr_plot, time, values[pow_lookup_curr["indices"]])
                    push!(volt_plot, time, values[pow_lookup_volt["indices"]])
                end
                
                mintime = min(cold_plot.times[]...)
                maxtime = max(cold_plot.times[]...)
                ylims!(cold_plot.axis, mintime, maxtime)
            end 
        catch e
            if e isa InterruptException
                println("thank you for flying with FOXSI")
                return 0
            end
        end
    end
end