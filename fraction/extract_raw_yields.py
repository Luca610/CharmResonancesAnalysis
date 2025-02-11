"""
Script to perform signal extraction as a function of pT for several BDT output scores for cut-variation method
"""

import os
import sys
import argparse
import numpy as np
from flarefly.data_handler import DataHandler
from flarefly.fitter import F2MassFitter
import yaml
import pdg
import ROOT

def check_config_consistency(cfg):
    pt_mins = cfg["pt_mins"]
    pt_maxs = cfg["pt_maxs"]
    mass_mins = cfg["fit"]["mass_mins"]
    mass_maxs = cfg["fit"]["mass_maxs"]
    sgn_funcs = cfg["fit"]["sgn_funcs"]
    bkg_funcs = cfg["fit"]["bkg_funcs"]
    bdt_bkg_cuts = cfg["bdt_cuts"]["bkg"]

    n = len(pt_mins)

    if len(pt_maxs) != n:
        print("pt_mins and pt_maxs have different length, check your config!") 
        sys.exit()
    if len(mass_mins) + len(mass_maxs) + len(sgn_funcs) + len(bkg_funcs) != 4*n:
        print("fit configuration length doesn't match number of pt bins, check your config!") 
        sys.exit()
    if isinstance(bdt_bkg_cuts, list) and len(bdt_bkg_cuts) != n:
        print("number of bkg cuts must be a single value or have the same length of the number of pt bins, check your config!") 
        sys.exit()


def perform_fit(file_name, histo_name, fitter_name, sgn_func, bkg_func, mass_min, mass_max, init_mass, part_name, signal_pars_tofix={}):
    """

    """
    data_hdl = DataHandler(file_name, varname = r"Inv Mass (GeV/c^2)", histoname=histo_name, limits=[mass_min, mass_max])
    fitter = F2MassFitter(data_hdl,
                              name_signal_pdf=[sgn_func],
                              name_background_pdf=[bkg_func],
                              name=fitter_name, tol=0.1)
    if part_name == "dstar":
        fitter.set_particle_mass(0, mass=init_mass, limits=[init_mass * 0.95, init_mass * 1.05])
        fitter.set_signal_initpar(0, "sigma", 0.0005, limits=[0.0001, 0.002])
        fitter.set_signal_initpar(0, "frac", 0.1)
        fitter.set_signal_initpar(0, "alphal", 1.5, limits=[1., 3.])
        fitter.set_signal_initpar(0, "alphar", 1.5, limits=[1., 3.])
        fitter.set_signal_initpar(0, "nl", 50, limits=[30., 100.])
        fitter.set_signal_initpar(0, "nr", 50, limits=[30., 100.])
        fitter.set_background_initpar(0, "power", 0.5)
        fitter.set_background_initpar(0, "c1", -20)
        fitter.set_background_initpar(0, "c2", 500)
        fitter.set_background_initpar(0, "c3", -5000)
    if part_name == "dplus":
        fitter.set_particle_mass(0, mass=init_mass, limits=[init_mass * 0.95, init_mass * 1.05])
        fitter.set_signal_initpar(0, "sigma", 0.005, limits=[0.0001, 0.04])
        fitter.set_signal_initpar(0, "frac", 0.1)
        fitter.set_background_initpar(0, "c0", 0.4)
        fitter.set_background_initpar(0, "c1", -0.2)
        fitter.set_background_initpar(0, "c2", -0.01)
        fitter.set_background_initpar(0, "c3", 0.01)
        
    if len(signal_pars_tofix) > 0:
        for par in signal_pars_tofix:
            fitter.set_signal_initpar(0, par, signal_pars_tofix[par], fix=True)

    fitter.mass_zfit()

    return fitter

# function to perform fits
def fit(input_config, fix_mean, plot_npcut):
    """
    Method for fitting
    """

    pdg_api = pdg.connect()

    with open(input_config, "r") as f:
        cfg = yaml.safe_load(f)

    if cfg["hadron"] not in ["dstar", "dplus"]:
        print(f"ERROR: {cfg['hadron']} not supported, exit")
        sys.exit()
    check_config_consistency(cfg)
    outputdir = cfg["output"]["rawyields"]["directory"]
    suffix = cfg["output"]["rawyields"]["suffix"]

    pt_mins = cfg["pt_mins"]
    pt_maxs = cfg["pt_maxs"]
    pt_limits = pt_mins.copy()
    pt_limits.append(pt_maxs[-1])
    pt_limits = np.array(pt_limits, np.float64)

    infile_name = os.path.join(outputdir, f"hist_mass{suffix}.root")

    mass_mins = cfg["fit"]["mass_mins"]
    mass_maxs = cfg["fit"]["mass_maxs"]
    sgn_funcs = cfg["fit"]["sgn_funcs"]
    bkg_funcs = cfg["fit"]["bkg_funcs"]
    bdt_np_mins = cfg["bdt_cuts"]["nonprompt"]

    # we first fit the high significance cases
    outfile_name_nocut = os.path.join(outputdir, f"rawyields_nocut{suffix}.root")
    outfile_nocut = ROOT.TFile(outfile_name_nocut, "recreate")
    outfile_nocut.Close()

    hist_rawyield_nocut = ROOT.TH1F(
        "hist_rawyield", ";#it{p}_{T} (GeV/#it{c}); raw yield", len(pt_mins), pt_limits)
    hist_sigma_nocut = ROOT.TH1F(
        "hist_sigma", ";#it{p}_{T} (GeV/#it{c}); #sigma (GeV/#it{c}^{2})", len(pt_mins), pt_limits)
    hist_mean_nocut = ROOT.TH1F(
        "hist_mean", ";#it{p}_{T} (GeV/#it{c}); #mu (GeV/#it{c}^{2})", len(pt_mins), pt_limits)
    hist_alphal_nocut = ROOT.TH1F(
        "hist_alphal", ";#it{p}_{T} (GeV/#it{c}); #alpha_{l}", len(pt_mins), pt_limits)
    hist_alphar_nocut = ROOT.TH1F(
        "hist_alphar", ";#it{p}_{T} (GeV/#it{c}); #alpha_{r}", len(pt_mins), pt_limits)
    hist_nl_nocut = ROOT.TH1F(
        "hist_nl", ";#it{p}_{T} (GeV/#it{c}); #it{n}_{l}", len(pt_mins), pt_limits)
    hist_nr_nocut = ROOT.TH1F(
        "hist_nr", ";#it{p}_{T} (GeV/#it{c}); #it{n}_{r}", len(pt_mins), pt_limits)

    hist_rawyield_nocut.SetDirectory(0)
    hist_sigma_nocut.SetDirectory(0)
    hist_mean_nocut.SetDirectory(0)
    hist_alphal_nocut.SetDirectory(0)
    hist_alphar_nocut.SetDirectory(0)
    hist_nl_nocut.SetDirectory(0)
    hist_nr_nocut.SetDirectory(0)

    hist_rawyield_cutvar = []
    for icut, _ in enumerate(bdt_np_mins):
        hist_rawyield_cutvar.append(
            ROOT.TH1F("hist_rawyield", ";#it{p}_{T} (GeV/#it{c}); raw yield", len(pt_mins), pt_limits))
        hist_rawyield_cutvar[icut].SetDirectory(0)

    fitter = []
    for ipt, (pt_min, pt_max) in enumerate(zip(pt_mins, pt_maxs)):
        if cfg["hadron"] == "dstar":
            mass = pdg_api.get_particle_by_mcid(413).mass - pdg_api.get_particle_by_mcid(421).mass
        if cfg["hadron"] == "dplus":
            mass = pdg_api.get_particle_by_mcid(411).mass
        fitter.append(
            perform_fit(infile_name,
                        f"hist_mass_pt{pt_min:.1f}_{pt_max:.1f}_nocutnp",
                        f"{cfg['hadron']}_pt{pt_min:.1f}_{pt_max:.1f}_nocutnp",
                        sgn_funcs[ipt],
                        bkg_funcs[ipt],
                        mass_mins[ipt],
                        mass_maxs[ipt],
                        mass,
                        cfg["hadron"])
        )

        pars_tofix = {}
        if fitter[ipt].get_fit_result.converged:
            rawyield = fitter[ipt].get_raw_yield(0)
            sigma = fitter[ipt].get_signal_parameter(0, "sigma")
            mean = fitter[ipt].get_mass(0)
            pars_tofix["sigma"] = sigma[0]
            if fix_mean:
                pars_tofix["mean"] = mean[0]
            hist_rawyield_nocut.SetBinContent(ipt+1, rawyield[0])
            hist_rawyield_nocut.SetBinError(ipt+1, rawyield[1])
            hist_sigma_nocut.SetBinContent(ipt+1, sigma[0])
            hist_sigma_nocut.SetBinError(ipt+1, sigma[1])
            hist_mean_nocut.SetBinContent(ipt+1, mean[0])
            hist_mean_nocut.SetBinError(ipt+1, mean[1])
            if sgn_funcs[ipt] == "doublecb":
                alphal = fitter[ipt].get_signal_parameter(0, "alphal")
                alphar = fitter[ipt].get_signal_parameter(0, "alphar")
                nl = fitter[ipt].get_signal_parameter(0, "nl")
                nr = fitter[ipt].get_signal_parameter(0, "nr")
                pars_tofix["alphal"] = alphal[0]
                pars_tofix["alphar"] = alphar[0]
                pars_tofix["nl"] = nl[0]
                pars_tofix["nr"] = nr[0]
                hist_alphal_nocut.SetBinContent(ipt+1, alphal[0])
                hist_alphal_nocut.SetBinError(ipt+1, alphal[1])
                hist_alphar_nocut.SetBinContent(ipt+1, alphar[0])
                hist_alphar_nocut.SetBinError(ipt+1, alphar[1])
                hist_nl_nocut.SetBinContent(ipt+1, nl[0])
                hist_nl_nocut.SetBinError(ipt+1, nl[1])
                hist_nr_nocut.SetBinContent(ipt+1, nr[0])
                hist_nr_nocut.SetBinError(ipt+1, nr[1])                

            fitter[ipt].dump_to_root(outfile_name_nocut,
                                     option="update",
                                     suffix=f"_pt{pt_min:.1f}_{pt_max:.1f}_nocutnp")
            xaxis = ""
            if cfg["hadron"] == "dstar":
                xaxis = r"$M(\mathrm{K}\pi\pi) - M(\mathrm{K}\pi)$ (GeV/$c^{2}$)"
            elif cfg["hadron"] == "dplus":
                xaxis = r"$M(\mathrm{K}\pi\pi)$ (GeV/$c^{2}$)"
            fig = fitter[ipt].plot_mass_fit(style="ATLAS", figsize=(8, 8), axis_title=xaxis, show_extra_info = True)
            figres = fitter[ipt].plot_raw_residuals(figsize=(8, 8), style="ATLAS")

            fig.savefig(
                os.path.join(outputdir, f"massfit{suffix}_pt{pt_min:.1f}_{pt_max:.1f}_nocutnp.pdf")
            )
            figres.savefig(
                os.path.join(outputdir, f"massfitres{suffix}_pt{pt_min:.1f}_{pt_max:.1f}_nocutnp.pdf")
            )

        fitter_pt_cutvar = []
        for icut, bdt_np_min in enumerate(bdt_np_mins):
            fitter_pt_cutvar.append(
                perform_fit(infile_name,
                            f"hist_mass_pt{pt_min:.1f}_{pt_max:.1f}_bdtnp{bdt_np_min:.2f}",
                            f"{cfg['hadron']}_pt{pt_min:.1f}_{pt_max:.1f}_bdtnp{bdt_np_min:.2f}",
                            sgn_funcs[ipt],
                            bkg_funcs[ipt],
                            mass_mins[ipt],
                            mass_maxs[ipt],
                            mass,
                            cfg["hadron"],
                            pars_tofix)
            )
            if fitter_pt_cutvar[icut].get_fit_result.converged:
                bin_counting_min = 0.14 if cfg["hadron"] == "dstar" else 1.70
                bin_counting_max = 0.16 if cfg["hadron"] == "dstar" else 2.00
                rawyield = fitter_pt_cutvar[icut].get_raw_yield_bincounting(
                    0, min=bin_counting_min, max=bin_counting_max)
                hist_rawyield_cutvar[icut].SetBinContent(ipt+1, rawyield[0])
                hist_rawyield_cutvar[icut].SetBinError(ipt+1, rawyield[1])
                if plot_npcut:
                    fig = fitter_pt_cutvar[icut].plot_mass_fit(style="ATLAS", figsize=(8, 8), axis_title=r"Inv Mass (GeV/c^2)", show_extra_info = True)
                    fig[0].savefig(
                        os.path.join(outputdir, "plots_npcut", f"massfit{suffix}_pt{pt_min:.1f}_{pt_max:.1f}_cutnp_{bdt_np_mins[icut]}.pdf")
                    )
                    

    for icut, bdt_np_min in enumerate(bdt_np_mins):
        outfile_name_cutvar = os.path.join(
            outputdir, f"rawyields_bdtnp{bdt_np_min:0.2f}{suffix}.root")
        outfile_cutvar = ROOT.TFile(outfile_name_cutvar, "recreate")
        hist_rawyield_cutvar[icut].Write()
        outfile_cutvar.Close()

    outfile_nocut = ROOT.TFile(outfile_name_nocut, "update")
    hist_rawyield_nocut.Write()
    hist_sigma_nocut.Write()
    hist_mean_nocut.Write()
    hist_alphal_nocut.Write()
    hist_alphar_nocut.Write()
    hist_nl_nocut.Write()
    hist_nr_nocut.Write()
    outfile_nocut.Close()


# function to project the sparse
def project(input_config):
    """
    
    """

    with open(input_config, "r") as f:
        cfg = yaml.safe_load(f)

    if cfg["hadron"] not in ["dstar", "dplus"]:
        print(f"ERROR: {cfg['hadron']} not supported, exit")
        sys.exit()

    infile_name = cfg["input"]["data"]
    outputdir = cfg["output"]["rawyields"]["directory"]
    suffix = cfg["output"]["rawyields"]["suffix"]

    infile = ROOT.TFile.Open(infile_name)
    sparse = infile.Get("hData")
    infile.Close()
    
    pt_mins = cfg["pt_mins"]
    pt_maxs = cfg["pt_maxs"]

    bdt_bkg_cuts = cfg["bdt_cuts"]["bkg"]
    if not isinstance(bdt_bkg_cuts, list):
        bdt_bkg_cuts = [bdt_bkg_cuts]*len(pt_mins)

    outfile = ROOT.TFile(os.path.join(outputdir, f"hist_mass{suffix}.root"), "recreate")

    histos_pt, histos_pt_cutvar = [], []
    for ipt, (pt_min, pt_max) in enumerate(zip(pt_mins, pt_maxs)):
        print(f'projecting in pt range {pt_min, pt_max}')
        bdt_bkg_bin_max = sparse.GetAxis(2).FindBin(bdt_bkg_cuts[ipt]*0.999)
        sparse.GetAxis(2).SetRange(1, bdt_bkg_bin_max)
        pt_bin_min = sparse.GetAxis(1).FindBin(pt_min*1.001)
        pt_bin_max = sparse.GetAxis(1).FindBin(pt_max*0.999)
        sparse.GetAxis(1).SetRange(pt_bin_min, pt_bin_max)
        histos_pt.append(sparse.Projection(0))
        histos_pt[ipt].SetName(f"hist_mass_pt{pt_min:.1f}_{pt_max:.1f}_nocutnp")
        outfile.cd()
        histos_pt[ipt].Write()
        histos_pt_cutvar.append([])
        for bdt_np_min in cfg["bdt_cuts"]["nonprompt"]:
            bdt_bkg_np_min = sparse.GetAxis(3).FindBin(bdt_np_min*1.001)
            sparse.GetAxis(3).SetRange(bdt_bkg_np_min, sparse.GetAxis(3).GetNbins()+1)
            histos_pt_cutvar[ipt].append(sparse.Projection(0))
            histos_pt_cutvar[ipt][-1].SetName(f"hist_mass_pt{pt_min:.1f}_{pt_max:.1f}_bdtnp{bdt_np_min:.2f}")
            outfile.cd()
            histos_pt_cutvar[ipt][-1].Write()
            sparse.GetAxis(3).SetRange(-1, -1)
    outfile.Close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arguments")
    parser.add_argument("--cfg_file", "-c", metavar="text",
                        default="config.yml", help="config file")
    parser.add_argument("--project", "-p", action="store_true",
                        default=False, help="enable projection")
    parser.add_argument("--fit", "-f", action="store_true",
                        default=False, help="enable fit w/o cut")
    parser.add_argument("--fix_mean", "-fm", action="store_true",
                        default=False, help="fix gaussian mean in fit")
    parser.add_argument("--plot_npcut", "-pl", action="store_true",
                        default=False, help="save all plots")
    args = parser.parse_args()

    if args.project:
        project(args.cfg_file)

    if args.fit:
        fit(args.cfg_file, args.fix_mean, args.plot_npcut)
