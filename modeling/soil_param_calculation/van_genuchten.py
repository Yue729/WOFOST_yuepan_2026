import numpy as np

class VanGenuchtenEquations():
    pF_FC = 2.0
    pF_SAT = -1.0
    pF_WP = 4.2

    def calculate_soil_moisture_content_from_pF(self, pF, alpha, n, theta_r, theta_s):
        psi = self.calculate_water_potential_form_pf(pF)
        theta = self.calculate_soil_moisture_content(psi, alpha, n, theta_r, theta_s)
        return theta

    def calculate_water_potential_form_pf(self, pF):
        psi = np.power(10, pF)
        return psi

    def calculate_soil_moisture_content(self, psi, alpha, n, theta_r, theta_s):
        theta = theta_r + (theta_s - theta_r) / np.power(1 + (np.power(alpha * psi, n)), 1 - 1 / n)
        return theta

    def calculate_hydraulic_conductivity(self, pF, alpha, labda, k_sat, n):
        psi = self.calculate_water_potential_form_pf(pF)
        m = 1 - 1 / n;
        ah = alpha * psi
        h1 = np.power(1 + np.power(ah, n), m)
        h2 = np.power(ah, n - 1)
        denom = np.power(1 + np.power(ah, n), m * (labda + 2));
        k_h = k_sat * np.power(h1 - h2, 2) / denom
        return k_h

class ClassicalSoilWaterBalanceParameterProvider(VanGenuchtenEquations):
    CRAIRC = 0.03
    RDMSOL = 120

    def __new__(cls, alpha, k_sat, n, theta_r, theta_s, CRAIRC = None, RDMSOL = None, SOPE = None):
        instance = object.__new__(cls)
        dict_cwb = instance.get_classical_waterbalance_pars(alpha, k_sat, n, theta_r, theta_s, CRAIRC, RDMSOL, SOPE)
        return dict_cwb

    def get_classical_waterbalance_pars(self, alpha, k_sat, n, theta_r, theta_s, CRAIRC, RDMSOL, SOPE):
        if RDMSOL is None:
            RDMSOL = self.RDMSOL
        else:
            pass
        if CRAIRC is None:
            CRAIRC = self.CRAIRC
        else:
            pass
        if SOPE is None:
            SOPE = k_sat
        else:
            SOPE = SOPE
        KSUB = k_sat
        SMFCF = self.calculate_soil_moisture_content_from_pF(self.pF_FC, alpha, n, theta_r, theta_s)
        SM0 = self.calculate_soil_moisture_content_from_pF(self.pF_SAT, alpha, n, theta_r, theta_s)
        SMW = self.calculate_soil_moisture_content_from_pF(self.pF_WP, alpha, n, theta_r, theta_s)
        dict_classical_waterbalance = dict(CRAIRC = CRAIRC, KSUB = KSUB, SOPE = SOPE, RDMSOL = RDMSOL, SMFCF=SMFCF, SM0=SM0, SMW=SMW)
        return dict_classical_waterbalance