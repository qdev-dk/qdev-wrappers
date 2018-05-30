import numpy as np
from qcodes.instrument.base import Instrument
from qcodes import validators as vals


#%% Create funciton for two-qubit readout and spectroscopy

class MultiQ_PulseBuilder(Instrument):
    def __init__(self,name,number_read_freqs,alazar,alazar_ctrl,awg,qubit,cavity,**kwargs):
        super().__init__(name, **kwargs)
        self.awg = awg
        self.qubit = qubit
        self.cavity = cavity
        self.alazar = alazar
        self.alazar_ctrl = alazar_ctrl
        self.filename = 'Waveforms'
        self.x_val = lambda: np.linspace(0,1,10)
        self.SR = 2.5e9
        self.number_read_freqs = number_read_freqs
        
        self.add_parameter('cycle_time',
                      label='Pulse Cycle Time',
                      unit='s',
                      set_cmd= lambda x : x,
                      vals=vals.Numbers(0,1e-3))
        self.add_parameter('int_time',
                      label='Integration time',
                      unit='s',
                      set_cmd= lambda x : x,
                      vals=vals.Numbers(0,0.2e-3))
        self.add_parameter('int_delay',
                      label='Readout Delay',
                      unit='s',
                      set_cmd= lambda x : x,
                      vals=vals.Numbers(0,0.2e-3))
        self.add_parameter('readout_dur',
                      label='Readout Duration',
                      unit='s',
                      set_cmd= lambda x : x,
                      vals=vals.Numbers(0,0.2e-3))
        self.add_parameter('marker_offset',
                      label='Marker Offset',
                      unit='s',
                      set_cmd= lambda x : x,
                      vals=vals.Numbers(-1e-5,1e-5))
        self.add_parameter('averages',
                      label='Averages',
                      unit='',
                      set_cmd=self.num_averages,
                      vals=vals.Numbers(1,1e5))
        for i in range(number_read_freqs):
            self.add_parameter('readout_freq_{}'.format(i+1),
                        label='Readout Frequency {}'.format(i+1),
                        unit='Hz',
                        set_cmd= lambda x : x,
                        vals=vals.Numbers(0,12.5e9))

        
    def MultiQ_SSB_Spectroscopy(self, start, stop, npts):
        qubitf = np.mean([start,stop])
        self.qubit.frequency(qubitf)
        self.x_val = lambda: np.linspace(start - qubitf,stop - qubitf,npts) + self.qubit.frequency()

        # Clear AWG
        self.awg.clearSequenceList()
        self.awg.clearWaveformList()
        
        N = int((self.cycle_time()*self.SR+64) - self.cycle_time()*self.SR%64)
        N_offset = int(self.marker_offset()*self.SR)
        time = np.linspace(N/self.SR-self.readout_dur(), N/self.SR, int(self.readout_dur()*self.SR), endpoint=False)
        
        # Create triggers
        ZerosMarker = np.zeros(int(N))
        TriggerMarker = np.zeros(int(N))
        TriggerMarker[-int(self.readout_dur()*self.SR-N_offset):-int(self.readout_dur()*self.SR-N_offset-500e-9*self.SR)] = 1
        
        # Create Drive tones
        wfms = [[], []]
        for i , f in enumerate(self.x_val()-qubitf):
            # SSB drive tone
            #sine_signal = np.concatenate((0.5*np.sin(f*2*np.pi*time),np.zeros(N-len(time))))
            #cosine_signal = np.concatenate((0.5*np.cos(f*2*np.pi*time),np.zeros(N-len(time))))
            sine_signal = np.concatenate((np.zeros(N-len(time)), 0.5*np.sin(f*2*np.pi*time)))
            cosine_signal = np.concatenate((np.zeros(N-len(time)), 0.5*np.cos(f*2*np.pi*time)))
            if i == 0:
                wfm_ch1 = np.array([cosine_signal,TriggerMarker,TriggerMarker])
                wfm_ch2 = np.array([sine_signal,TriggerMarker,TriggerMarker])
            else:
                wfm_ch1 = np.array([cosine_signal,ZerosMarker,ZerosMarker])
                wfm_ch2 = np.array([sine_signal,ZerosMarker,ZerosMarker])
            wfms[0].append(wfm_ch1)
            wfms[1].append(wfm_ch2)

        trig_waits = [0 for _ in range(npts)] 
        nreps = [1 for _ in range(npts)] 
        event_jumps = [0 for _ in range(npts)]
        event_jump_to = [0 for _ in range(npts)]
        go_to = [0 for _ in range(npts)]
        go_to[-1] = 1 # Make the sequence loop back to first step

        seqx = self.awg.makeSEQXFile(trig_waits,
                                nreps,
                                event_jumps,
                                event_jump_to,
                                go_to,
                                wfms,
                                [1, 1],
                                self.filename)
        self.awg.sendSEQXFile(seqx, self.filename + '.seqx')
        self.awg.loadSEQXFile(self.filename + '.seqx')
        
        # Create Readout tones
        self.update_readout_freqs()

        # Create sequence for readout tones SLISt:SEQuence:NEW <sequence_name>,<number_of_steps> [,<number_of_tracks>]
        self.awg.write('SLISt:SEQuence:NEW \"Readout_Seq\", {}, 2'.format(npts))
        self.awg.write('SLISt:SEQuence:STEP{}:GOTO \"Readout_Seq\", 1'.format(npts))
        # Fill Readout waveforms into sequence
        for i in range(npts):
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet1:WAVeform \"Readout_Seq\", \"Readout_I\"'.format(str(i+1)))
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet2:WAVeform \"Readout_Seq\", \"Readout_Q\"'.format(str(i+1)))

        # Assign waveforms
        self.awg.ch1.setSequenceTrack(self.filename, 1)
        self.awg.ch2.setSequenceTrack(self.filename, 2)
        self.awg.ch3.setSequenceTrack('Readout_Seq', 1)
        self.awg.ch4.setSequenceTrack('Readout_Seq', 2)
        self.awg.ch2.state(1)
        self.awg.play()
        
        # ALazar labels
        self.alazar.seq_mode('on')
        for ala_chan in self.alazar_ctrl.channels[2:4]:
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('SSB Drive frequency',ala_chan.data.setpoint_labels[1])
            ala_chan.data.setpoint_units = ('Hz',ala_chan.data.setpoint_units[1])

        for n, ala_chan in enumerate(self.alazar_ctrl.channels[12:20]):
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('SSB Drive frequency',)
            ala_chan.data.setpoint_units = ('Hz',)

        # prepare channels
        self.num_averages(self._averages)

    def MultiQ_SSB_Spec_NoOverlap(self, start, stop, npts, pulse_length = 2e-6):
        qubitf = np.mean([start,stop])
        self.qubit.frequency(qubitf)
        self.x_val = lambda: np.linspace(start - qubitf,stop - qubitf,npts) + self.qubit.frequency()

        # Clear AWG
        self.awg.clearSequenceList()
        self.awg.clearWaveformList()
        
        N = int((self.cycle_time()*self.SR+64) - self.cycle_time()*self.SR%64)
        N_offset = int(self.marker_offset()*self.SR)
        time = np.linspace(0, pulse_length, int(pulse_length*self.SR), endpoint=False)
        
        # Create triggers
        ZerosMarker = np.zeros(int(N))
        TriggerMarker = np.zeros(int(N))
        TriggerMarker[-int(self.readout_dur()*self.SR-N_offset):-int(self.readout_dur()*self.SR-N_offset-500e-9*self.SR)] = 1
        
        # Create Drive tones
        wfms = [[], []]
        for i , f in enumerate(self.x_val()-qubitf):
            # SSB drive tone
            sine_signal = np.concatenate((np.zeros(N-len(time)-int(self.readout_dur()*self.SR)), 0.5*np.sin(f*2*np.pi*time),np.zeros(int(self.readout_dur()*self.SR))))
            cosine_signal = np.concatenate((np.zeros(N-len(time)-int(self.readout_dur()*self.SR)), 0.5*np.cos(f*2*np.pi*time),np.zeros(int(self.readout_dur()*self.SR))))
            if i == 0:
                wfm_ch1 = np.array([cosine_signal,TriggerMarker,TriggerMarker])
                wfm_ch2 = np.array([sine_signal,TriggerMarker,TriggerMarker])
            else:
                wfm_ch1 = np.array([cosine_signal,ZerosMarker,ZerosMarker])
                wfm_ch2 = np.array([sine_signal,ZerosMarker,ZerosMarker])
            wfms[0].append(wfm_ch1)
            wfms[1].append(wfm_ch2)

        trig_waits = [0 for _ in range(npts)] 
        nreps = [1 for _ in range(npts)] 
        event_jumps = [0 for _ in range(npts)]
        event_jump_to = [0 for _ in range(npts)]
        go_to = [0 for _ in range(npts)]
        go_to[-1] = 1 # Make the sequence loop back to first step

        seqx = self.awg.makeSEQXFile(trig_waits,
                                nreps,
                                event_jumps,
                                event_jump_to,
                                go_to,
                                wfms,
                                [1, 1],
                                self.filename)
        self.awg.sendSEQXFile(seqx, self.filename + '.seqx')
        self.awg.loadSEQXFile(self.filename + '.seqx')
        
        # Create Readout tones
        self.update_readout_freqs()

        # Create sequence for readout tones SLISt:SEQuence:NEW <sequence_name>,<number_of_steps> [,<number_of_tracks>]
        self.awg.write('SLISt:SEQuence:NEW \"Readout_Seq\", {}, 2'.format(npts))
        self.awg.write('SLISt:SEQuence:STEP{}:GOTO \"Readout_Seq\", 1'.format(npts))
        # Fill Readout waveforms into sequence
        for i in range(npts):
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet1:WAVeform \"Readout_Seq\", \"Readout_I\"'.format(str(i+1)))
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet2:WAVeform \"Readout_Seq\", \"Readout_Q\"'.format(str(i+1)))

        # Assign waveforms
        self.awg.ch1.setSequenceTrack(self.filename, 1)
        self.awg.ch2.setSequenceTrack(self.filename, 2)
        self.awg.ch3.setSequenceTrack('Readout_Seq', 1)
        self.awg.ch4.setSequenceTrack('Readout_Seq', 2)
        self.awg.ch2.state(1)
        self.awg.play()
        
        # ALazar labels
        self.alazar.seq_mode('on')
        for ala_chan in self.alazar_ctrl.channels[2:4]:
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('SSB Drive frequency',ala_chan.data.setpoint_labels[1])
            ala_chan.data.setpoint_units = ('Hz',ala_chan.data.setpoint_units[1])

        for n, ala_chan in enumerate(self.alazar_ctrl.channels[12:20]):
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('SSB Drive frequency',)
            ala_chan.data.setpoint_units = ('Hz',)

        # prepare channels
        self.num_averages(self._averages)

    def MultiQ_Rabi(self, start, stop, npts):

        self.x_val = lambda: np.linspace(start ,stop ,npts)

        # Clear AWG
        self.awg.ch2.state(0)
        self.awg.clearSequenceList()
        self.awg.clearWaveformList()
        
        N = int((self.cycle_time()*self.SR+64) - self.cycle_time()*self.SR%64)
        N_offset = int(self.marker_offset()*self.SR)
        
        # Create triggers
        ZerosMarker = np.zeros(int(N))
        TriggerMarker = np.zeros(int(N))
        TriggerMarker[-int(self.readout_dur()*self.SR-N_offset):-int(self.readout_dur()*self.SR-N_offset-500e-9*self.SR)] = 1
        
        # Create Drive tones
        wfms = [[]]
        for i , t in enumerate(self.x_val()):
            # SSB drive tone
            drive = np.zeros(int(N))
            drive[-int((self.readout_dur() + t)*self.SR):-int(self.readout_dur()*self.SR)] = 0.5
            if i == 0:
                wfm_ch1 = np.array([drive,TriggerMarker,TriggerMarker])
            else:
                wfm_ch1 = np.array([drive,ZerosMarker,ZerosMarker])
            wfms[0].append(wfm_ch1)
            
        trig_waits = [0 for _ in range(npts)] 
        nreps = [1 for _ in range(npts)] 
        event_jumps = [0 for _ in range(npts)]
        event_jump_to = [0 for _ in range(npts)]
        go_to = [0 for _ in range(npts)]
        go_to[-1] = 1 # Make the sequence loop back to first step

        seqx = self.awg.makeSEQXFile(trig_waits,
                                nreps,
                                event_jumps,
                                event_jump_to,
                                go_to,
                                wfms,
                                [1],
                                self.filename)
        self.awg.sendSEQXFile(seqx, self.filename + '.seqx')
        self.awg.loadSEQXFile(self.filename + '.seqx')
        
        # Create Readout tones
        self.update_readout_freqs()

        # Create sequence for readout tones SLISt:SEQuence:NEW <sequence_name>,<number_of_steps> [,<number_of_tracks>]
        self.awg.write('SLISt:SEQuence:NEW \"Readout_Seq\", {}, 2'.format(npts))
        self.awg.write('SLISt:SEQuence:STEP{}:GOTO \"Readout_Seq\", 1'.format(npts))
        # Fill Readout waveforms into sequence
        for i in range(npts):
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet1:WAVeform \"Readout_Seq\", \"Readout_I\"'.format(str(i+1)))
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet2:WAVeform \"Readout_Seq\", \"Readout_Q\"'.format(str(i+1)))

        # Assign waveforms
        self.awg.ch1.setSequenceTrack(self.filename, 1)
        self.awg.ch3.setSequenceTrack('Readout_Seq', 1)
        self.awg.ch4.setSequenceTrack('Readout_Seq', 2)
        self.awg.play()
        
        # ALazar labels
        self.alazar.seq_mode('on')
        for ala_chan in self.alazar_ctrl.channels[2:4]:
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('Drive time',ala_chan.data.setpoint_labels[1])
            ala_chan.data.setpoint_units = ('s',ala_chan.data.setpoint_units[1])

        for n, ala_chan in enumerate(self.alazar_ctrl.channels[12:20]):
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('Drive time',)
            ala_chan.data.setpoint_units = ('s',)

        # prepare channels
        self.num_averages(self._averages)

    def MultiQ_Lifetime(self, start, stop, npts, pipulse = 10e-9):

        self.x_val = lambda: np.linspace(start ,stop ,npts)

        # Clear AWG
        self.awg.ch2.state(0)
        self.awg.clearSequenceList()
        self.awg.clearWaveformList()
        
        N = int((self.cycle_time()*self.SR+64) - self.cycle_time()*self.SR%64)
        N_offset = int(self.marker_offset()*self.SR)
        
        # Create triggers
        ZerosMarker = np.zeros(int(N))
        TriggerMarker = np.zeros(int(N))
        TriggerMarker[-int(self.readout_dur()*self.SR-N_offset):-int(self.readout_dur()*self.SR-N_offset-500e-9*self.SR)] = 1
        
        # Create Drive tones
        wfms = [[]]
        for i , t in enumerate(self.x_val()):
            # SSB drive tone
            drive = np.zeros(int(N))
            drive[-int((self.readout_dur() + t + pipulse)*self.SR):-int((self.readout_dur() + t)*self.SR)] = 0.5
            if i == 0:
                wfm_ch1 = np.array([drive,TriggerMarker,TriggerMarker])
            else:
                wfm_ch1 = np.array([drive,ZerosMarker,ZerosMarker])
            wfms[0].append(wfm_ch1)
            
        trig_waits = [0 for _ in range(npts)] 
        nreps = [1 for _ in range(npts)] 
        event_jumps = [0 for _ in range(npts)]
        event_jump_to = [0 for _ in range(npts)]
        go_to = [0 for _ in range(npts)]
        go_to[-1] = 1 # Make the sequence loop back to first step

        seqx = self.awg.makeSEQXFile(trig_waits,
                                nreps,
                                event_jumps,
                                event_jump_to,
                                go_to,
                                wfms,
                                [1],
                                self.filename)
        self.awg.sendSEQXFile(seqx, self.filename + '.seqx')
        self.awg.loadSEQXFile(self.filename + '.seqx')
        
        # Create Readout tones
        self.update_readout_freqs()

        # Create sequence for readout tones SLISt:SEQuence:NEW <sequence_name>,<number_of_steps> [,<number_of_tracks>]
        self.awg.write('SLISt:SEQuence:NEW \"Readout_Seq\", {}, 2'.format(npts))
        self.awg.write('SLISt:SEQuence:STEP{}:GOTO \"Readout_Seq\", 1'.format(npts))
        # Fill Readout waveforms into sequence
        for i in range(npts):
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet1:WAVeform \"Readout_Seq\", \"Readout_I\"'.format(str(i+1)))
            self.awg.write('SLISt:SEQuence:STEP{}:TASSet2:WAVeform \"Readout_Seq\", \"Readout_Q\"'.format(str(i+1)))

        # Assign waveforms
        self.awg.ch1.setSequenceTrack(self.filename, 1)
        self.awg.ch3.setSequenceTrack('Readout_Seq', 1)
        self.awg.ch4.setSequenceTrack('Readout_Seq', 2)
        self.awg.play()
        
        
        # ALazar labels
        self.alazar.seq_mode('on')
        for ala_chan in self.alazar_ctrl.channels[2:4]:
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('Wait time',ala_chan.data.setpoint_labels[1])
            ala_chan.data.setpoint_units = ('s',ala_chan.data.setpoint_units[1])

        for n, ala_chan in enumerate(self.alazar_ctrl.channels[12:20]):
            ala_chan.records_per_buffer(npts)
            ala_chan.data.setpoint_labels = ('Wait time',)
            ala_chan.data.setpoint_units = ('s',)

        # prepare channels
        self.num_averages(self._averages)

    def set_readout_freqs(self,readout_frequencies):
        if len(readout_frequencies) != self.number_read_freqs:
            raise ValueError('Number of given readout frequencies has to \
                                be {}.'.format(self.number_read_freqs))
        for i in range(self.number_read_freqs):
            ret.append(getattr(self,'readout_freq_{}'.format(i+1))(readout_frequencies[i]))
        self.update_readout_freqs()

    def get_readout_freqs(self):
        ret = []
        for i in range(self.number_read_freqs):
            ret.append(getattr(self,'readout_freq_{}'.format(i+1))())
        return np.array(ret)

    def update_readout_freqs(self):
        readout_freqs = self.get_readout_freqs()
        N = int((self.cycle_time()*self.SR+64) - self.cycle_time()*self.SR%64)

        N_offset = int(self.marker_offset()*self.SR)
        # Create trigger
        TriggerMarker = np.zeros(N)
        TriggerMarker[-int(self.readout_dur()*self.SR-N_offset):-int(self.readout_dur()*self.SR-N_offset-500e-9*self.SR)] = 1
    
        # Readout tones
        time = np.linspace(0, self.readout_dur(), int(self.readout_dur()*self.SR), endpoint=False)
        cosine_readout = np.zeros(N)
        sine_readout = np.zeros(N)
        for fr in readout_freqs:
            fi = fr - self.cavity.frequency()
            cosine_readout += (0.5/len(readout_freqs))*np.concatenate((np.zeros(N-len(time)),np.cos(fi*2*np.pi*time)))
            sine_readout += (0.5/len(readout_freqs))*np.concatenate((np.zeros(N-len(time)),np.sin(fi*2*np.pi*time)))
        wfm_ch3 = np.array([cosine_readout,TriggerMarker,TriggerMarker])
        wfm_ch4 = np.array([sine_readout,TriggerMarker,TriggerMarker])
        
        state = self.awg.run_state()
        self.awg.stop()
        wfm_ch3_file = self.awg.makeWFMXFile(wfm_ch3, 1)
        wfm_ch4_file = self.awg.makeWFMXFile(wfm_ch4, 1)
        self.awg.sendWFMXFile(wfm_ch3_file, 'Readout_I.wfmx')
        self.awg.sendWFMXFile(wfm_ch4_file, 'Readout_Q.wfmx')
        self.awg.loadWFMXFile('Readout_I.wfmx')
        self.awg.loadWFMXFile('Readout_Q.wfmx')
        # Only start play if running to begin with
        if state == 'Running':
            self.awg.play()
        
        # Set demod frequencies
        for ala_chan in self.alazar_ctrl.channels[2:4]:
            ala_chan.demod_freq(abs(readout_freqs[0]-self.cavity.frequency()))
            
        for n, ala_chan in enumerate(self.alazar_ctrl.channels[4:12]):
            try:
                ala_chan.demod_freq(abs(readout_freqs[n//2]-self.cavity.frequency()))
            except:
                pass
        for n, ala_chan in enumerate(self.alazar_ctrl.channels[12:20]):
            try:
                ala_chan.demod_freq(abs(readout_freqs[n//2]-self.cavity.frequency()))
            except:
                pass

    def num_averages(self,value):
        self._averages = value
        self.alazar_ctrl.int_time(self.int_time())
        self.alazar_ctrl.int_delay(self.int_delay())
        for ala_chan in self.alazar_ctrl.channels[2:4]:
            ala_chan.num_averages(value)
            ala_chan.prepare_channel()
            ala_chan.data.setpoints = (tuple(self.x_val()),ala_chan.data.setpoints[1])
            
        for ala_chan in self.alazar_ctrl.channels[4:12]:
            ala_chan.num_averages(value)
            ala_chan.prepare_channel()
            
        for ala_chan in self.alazar_ctrl.channels[12:20]:
            ala_chan.num_averages(value)
            ala_chan.prepare_channel()
            ala_chan.data.setpoints = (tuple(self.x_val()),)