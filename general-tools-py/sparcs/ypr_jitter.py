import os
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
import pandas as pd

files = [
    '../../../../NSROC/SPARCS/reference/Glesener/fine/glesener_flare.csv',
    '../../../../NSROC/SPARCS/reference/Glesener/fine/glesener_ar.csv',
    # '../../../../NSROC/SPARCS/reference/Glesener/fine/glesener.csv',
    '../../../../NSROC/SPARCS/reference/Winebarger/winebarger.csv', 
    '../../../../NSROC/SPARCS/reference/Kankelborg/kankelborg.csv', 
    '../../../../NSROC/SPARCS/reference/Chamberlin/chamberlin_p1.csv', 
    '../../../../NSROC/SPARCS/reference/Chamberlin/chamberlin_p3.csv',
    '../../../../NSROC/SPARCS/reference/Chamberlin/chamberlin_t360-t460.csv',
]

if __name__ == "__main__":
    for f in files:
        print(os.path.abspath(f))
        df = pd.read_csv(os.path.abspath(f),header=0)
        title = os.path.basename(f).split('.')[0].title()
        prefix = os.path.abspath(os.path.dirname(f))
        print(prefix)

        # make yaw and pitch relative to mean:
        yaw_rel = df['yaw'] - np.mean(df['yaw'])
        pitch_rel = df['pitch'] - np.mean(df['pitch'])

        # check if this is Chamberlin (no provided timestamps, yet)...
        timeprefix = ''
        if 'yawtime' in df.keys():
            time = df['yawtime'].to_numpy()
        else:
            # if no timestamps, just make something up for the plot.
            timeprefix = '[FAKE TIME DATA] '
            time = np.linspace(0, 0.02*len(yaw_rel), len(yaw_rel))

        # fft both yaw and pitch
        yaw_spec = np.fft.fft(yaw_rel)
        pitch_spec = np.fft.fft(pitch_rel)

        # get spectral magnitude from fft
        yaw_spec_mag = np.sqrt(np.square(yaw_spec.real) + np.square(yaw_spec.imag))
        pitch_spec_mag = np.sqrt(np.square(pitch_spec.real) + np.square(pitch_spec.imag))
        # get spectral phase from fft
        yaw_spec_pha = np.atan2(yaw_spec.imag, yaw_spec.real)
        pitch_spec_pha = np.atan2(pitch_spec.imag, pitch_spec.real)

        # get frequency bins for the fft:
        freq = np.fft.fftfreq(len(time), d=np.mean(np.diff(time)))

        # magnitude of off-pointing:
        rms = np.sqrt(np.square(yaw_rel) + np.square(pitch_rel))
        sum = yaw_rel + pitch_rel

        # plt_mosaic = [
        #     ['phase', 'phase_cbar', 'fft_mag'],
        #     ['phase', 'phase_cbar', 'fft_phase'],
        #     ['phase', 'phase_cbar', 'rms'],
        #     ['phase', 'phase_cbar', 'sum'],
        # ]
        plt_mosaic = [
            ['yaw',     'phase',    'phase_cbar'],
            ['pitch',   'phase',    'phase_cbar'],
            ['sum',     'fft_mag',  'fft_mag'],
            ['rms',     'fft_phase','fft_phase']
        ]

        fig = None
        ax = None
        colormap = 'cividis'
        # fig, ax = plt.subplot_mosaic(plt_mosaic, figsize=(8,8), width_ratios=[5,1,5], height_ratios=[1,1,1,1], layout='tight', empty_sentinel='BLANK')
        fig, ax = plt.subplot_mosaic(plt_mosaic, figsize=(8,8), width_ratios=[5,5,1], height_ratios=[1,1,1,1], layout='tight', empty_sentinel='BLANK')
        fig.suptitle(title)
        ax['phase'].scatter(yaw_rel, pitch_rel, c=range(len(yaw_rel)), s=0.1, cmap=colormap)
        ax['phase'].set_xlabel('yaw [arcsec]')
        ax['phase'].set_ylabel('pitch [arcsec]')
        ax['phase'].set_xlim([-1.5, 1.5])
        ax['phase'].set_ylim([-1.5, 1.5])
        ax['phase'].set_aspect('equal')
        ax['phase'].grid(visible=True, which='major', axis='both')
        ax['phase'].set_title('Pointing (no roll correction)')
        ax['phase'].set_xticks(np.arange(-1.5, 1.5, 0.5))
        ax['phase'].set_yticks(np.arange(-1.5, 1.5, 0.5))

        ax['fft_mag'].plot(freq, yaw_spec_mag, freq, pitch_spec_mag)
        ax['fft_mag'].set_xlim([0,ax['fft_mag'].get_xlim()[1]])
        ax['fft_mag'].set_xlabel(timeprefix + 'frequency [Hz]')
        ax['fft_mag'].set_ylabel('magnitude')
        # ax['fft_mag'].set_xlim([0, 10])
        ax['fft_mag'].grid(visible=True, which='major', axis='both')
        ax['fft_mag'].set_title('Yaw/pitch spectrum—magnitude')
        ax['fft_mag'].legend(['yaw', 'pitch'],fontsize='small')

        ax['fft_phase'].plot(freq, 180*yaw_spec_pha/np.pi, freq, 180*pitch_spec_pha/np.pi)
        ax['fft_phase'].set_xlim([0,ax['fft_phase'].get_xlim()[1]])
        ax['fft_phase'].set_xlabel(timeprefix + 'frequency [Hz]')
        ax['fft_phase'].set_ylabel('phase [deg]')
        ax['fft_phase'].grid(visible=True, which='major', axis='both')
        ax['fft_phase'].set_title('Yaw/pitch spectrum—phase')
        ax['fft_phase'].legend(['yaw', 'pitch'],fontsize='small')

        ax['fft_phase'].sharex(ax['fft_mag'])

        ax['yaw'].scatter(time, yaw_rel, c=range(len(rms)), s=0.1, cmap=colormap)
        ax['yaw'].set_xlabel(timeprefix + 'time [s]')
        ax['yaw'].set_ylabel('yaw [arcsec]')
        ax['yaw'].grid(visible=True, which='major', axis='both')
        ax['yaw'].set_title('Yaw') 

        ax['pitch'].scatter(time, pitch_rel, c=range(len(rms)), s=0.1, cmap=colormap)
        ax['pitch'].set_xlabel(timeprefix + 'time [s]')
        ax['pitch'].set_ylabel('pitch [arcsec]')
        ax['pitch'].grid(visible=True, which='major', axis='both')
        ax['pitch'].set_title('Pitch') 

        ax['rms'].scatter(time, rms, c=range(len(rms)), s=0.1, cmap=colormap)
        ax['rms'].set_xlabel(timeprefix + 'time [s]')
        ax['rms'].set_ylabel('magnitude [arcsec]')
        ax['rms'].grid(visible=True, which='major', axis='both')
        ax['rms'].set_title('Offpointing magnitude') 

        ax['sum'].scatter(time, sum, c=range(len(sum)), s=0.1, cmap=colormap)
        ax['sum'].set_xlabel(timeprefix + 'time [s]')
        ax['sum'].set_ylabel('yaw + pitch [arcsec]')
        ax['sum'].grid(visible=True, which='major', axis='both')
        ax['sum'].set_title('Sum of yaw and pitch')
        
        ax['yaw'].sharex(ax['pitch'])
        ax['rms'].sharex(ax['pitch'])
        ax['sum'].sharex(ax['pitch'])

        plt.tight_layout()
        
        ax['phase_cbar'].set_position([ax['phase'].get_position().x1+0.01, ax['phase'].get_position().y0, 0.02, ax['phase'].get_position().height])
        cbar = fig.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(time[0], time[-1]), cmap=colormap),
             cax=ax['phase_cbar'], orientation='vertical', ticks=[time[0], time[-1]])
        cbar.ax.set_yticklabels(['T+'+str(time[0]), 'T+'+str(time[-1])], fontsize='small')
        cbar.set_label(timeprefix + 'Time', labelpad=-40)

        outpath = os.path.join(prefix, title + '.pdf')
        print('saving figure to ', outpath)
        fig.savefig(outpath,transparent=True)

    plt.show()