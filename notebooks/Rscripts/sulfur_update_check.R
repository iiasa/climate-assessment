# Visualising sulfur historical emissions of AR6 climate assessment workflow
# Do:
# - [x] visualise RCMIP (used in AR6)
# - [x] visualise CEDS 2024 update
# - [x] visualise difference between RCMIP and CEDS
# - [ ] write out Sulfur data from CEDS for global emissions


library(tidyverse)
library(geomtextpath)
library(here)
try(setwd(dirname(rstudioapi::getActiveDocumentContext()$path)))
here::i_am("README.rst")

# Data -------------------------------------------------------------------------

### RCMIP ----------------------------------------------------------------------
rcmip.emssions <- read_csv(here("src",
                                "climate_assessment",
                                "harmonization",
                                "history_ar6.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))

### CEDS 2024 ------------------------------------------------------------------
# [ ] move file to climate-assessment folder if we start using it
##### SO2 ----------------------------------------------------------------------
ceds.emssions.sulfur <- read_csv(
  "C:/Users/kikstra/OneDrive - IIASA/_Other/Data/Emissions data/CEDS/CEDS_v_2024_04_01_aggregate/SO2_CEDS_emissions_by_country_v2024_04_01.csv"
) %>%
  pivot_longer(cols = -c(em,country,units),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(substr(Year, 2, 5))) %>%
  summarise(
    value = sum(value, na.rm = TRUE)*1e3/1e6,
    Unit = "Mt SO2/yr",
    Variable = "SO2 (CEDS, Jan 2024 update)",
    .by = c("Year")
  )


##### Save: SO2 emissions ------------------------------------------------------
ceds.emssions.sulfur.wide <- ceds.emssions.sulfur %>% pivot_wider(names_from = Year, values_from = value)

write_delim(
  x = ceds.emssions.sulfur.wide,
  file = here("notebooks", "Rscripts", "output-data", "sulfur_emissions_CEDS_global.csv"),
  delim = ","
)


### Future emissions (CMIP6) ---------------------------------------------------
cmip6.emssions <- read_csv(here("src",
                                "climate_assessment",
                                "infilling",
                                "cmip6-ssps-workflow-emissions.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))

### Future emissions (Infiller database AR6) -----------------------------------
ar6.inf.emssions <- read_csv(here("tests",
                                "test-data",
                                "ar6_vetted_infillerdatabase.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))

### Future emissions (stanadrd database AR6) -----------------------------------
ar6.emssions <- read_csv(here("tests",
                                  "test-data",
                                  "ar6_vetted_infillerdatabase.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))


### AR6 Metadata ---------------------------------------------------------------
ar6.metadata <- readxl::read_excel(
  "C:/Users/kikstra/OneDrive - IIASA/_Other/Data/Scenario data/Scenario Databases/AR6_Scenarios_Database_World_v1.1/AR6_Scenarios_Database_metadata_indicators_v1.1.xlsx",
  sheet = "meta_Ch3vetted_withclimate"
) %>% select(Model,Scenario,Category)



# Visualisation (historical emissions) -----------------------------------------

### Sulfur ---------------------------------------------------------------------
sulfur.hist <- rcmip.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Sulfur (historical, AR6, RCMIP)") %>%
  bind_rows(ceds.emssions.sulfur)

p.sulfur.hist <- ggplot(sulfur.hist %>% filter(Year >= 1970),
                        aes(x=Year, y=value, color=Variable)) +
  geom_line() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Historical sulfur emissions",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.hist


# Visualisation (future emissions) ---------------------------------------------

### Sulfur ---------------------------------------------------------------------
sulfur.scens.cmip6 <- cmip6.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, CMIP6)")
sulfur.scens.ar6 <- ar6.inf.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, AR6 default)")

p.sulfur.scens <- ggplot(sulfur.hist %>% filter(Year >= 1990),
                        aes(x=Year, y=value, color=Variable)) +
  geom_line(linewidth=1.5) +
  geom_line(data = sulfur.scens.ar6 %>% filter(Year>=2015,Year<=2050),
                aes(x=Year, y=value, group=interaction(Model,Scenario)),
                colour = "grey",
                linetype = "solid", alpha = 0.1) +
  geom_line(data = sulfur.scens.ar6 %>% filter(Year>=2015,Year<=2050) %>%
              left_join(ar6.metadata) %>%
              filter(Category=="C1"),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "dodgerblue",
            linetype = "solid", alpha = 0.1) +
  geom_textline(data = sulfur.scens.cmip6 %>% filter(Year>=2015,Year<=2050),
                aes(x=Year, y=value, group=interaction(Model,Scenario), label = Scenario),
                linetype = "dashed",
                colour = "black",
                hjust=0.9) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c("blue", "red")) +
  labs(
    title = "Historical sulfur emissions",
    subtitle = "Grey: harmonized emissions AR6,\nLight blue: C1 scenarios",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.scens

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions.pdf"),
       plot = p.sulfur.scens, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions.png"),
       plot = p.sulfur.scens,
       width = 300, height = 200, dpi = 300, units = "mm")



# Visualisation (historical emissions difference) ------------------------------
sulfur.hist.diff <- rcmip.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Sulfur (historical, AR6, RCMIP)") %>%
  bind_rows(ceds.emssions.sulfur) %>%
  select(Variable,Unit,Year,value) %>%
  pivot_wider(names_from = Variable, values_from = value) %>%
  mutate(diff = `SO2 (CEDS, Jan 2024 update)` - `Sulfur (historical, AR6, RCMIP)`) %>%
  mutate(diff.rel.to.rcmip = diff / `Sulfur (historical, AR6, RCMIP)`)


p.sulfur.hist.diff <- ggplot(sulfur.hist.diff %>% filter(Year >= 1970),
                        aes(x=Year, y=diff.rel.to.rcmip)) +
  geom_line() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Historical sulfur emissions (difference)",
    x = "Year",
    y = "% difference from AR6"
  ) +
  # scale y axis to percentages
  scale_y_continuous(labels = scales::percent) +
  theme_minimal()
p.sulfur.hist.diff

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_hist_diff.pdf"),
       plot = p.sulfur.hist.diff, device = cairo_pdf,
       width = 200, height = 100, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_hist_diff.png"),
       plot = p.sulfur.hist.diff,
       width = 200, height = 100, dpi = 300, units = "mm")




# Create new CMIP6 emissions dataset (all vetted scenarios) --------------------
ar6.data.location.global <- "C:/Users/kikstra/OneDrive - IIASA/_Other/Data/Scenario data/Scenario Databases/AR6_Scenarios_Database_World_v1.1"
ar6.data.file.global <- "AR6_Scenarios_Database_World_v1.1.csv"
ar6.meta.file <- "AR6_Scenarios_Database_metadata_indicators_v1.1.xlsx"

ar6.meta <- read_excel(file.path(ar6.data.location.global, ar6.meta.file),
                       sheet = "meta"
                       # sheet = "meta_Ch3vetted_withclimate"
                       ) %>%
  select(Model, Scenario,
         Category) %>%
  filter(Category!="failed-vetting")

ar6.data.emissions <- vroom(
  file.path(
    ar6.data.location.global,
    ar6.data.file.global
  )
) %>%
  left_join(ar6.meta) %>%
  drop_na(Category) %>% select(-Category) %>%
  filter(str_detect(Variable, "^Emissions")) # in regex, the ^ symbol indicates the beginning of a string

write_delim(
  x = ar6.data.emissions,
  file = here("notebooks", "Rscripts", "output-data", "ar6_emissions_vettedscenarios.csv"),
  delim = ",",
  na = ""
)








# Create new CMIP6 emissions dataset (all vetted scenarios) --------------------
ar6.inf.emssions.newCEDSso2 <- read_csv(here("output",
                                             "switch full sulfur timeseries to CEDS",
                                  "ar6_emissions_vettedscenarios_harmonized.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))

ar6.inf.emssions.newCEDSso2.method2040 <- read_csv(here("output",
                                             "switch sulfur 2015 to CEDS and change harmonization method",
                                             "ar6_emissions_vettedscenarios_harmonized.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))

### new harmonized emissions (only updated CEDS sulfur) ------------------------
sulfur.scens.cmip6 <- cmip6.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, CMIP6)")
sulfur.scens.ar6.newCEDSso2 <- ar6.inf.emssions.newCEDSso2 %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, with updated 2015 CEDS)")

p.sulfur.scens.newCEDSso2 <- ggplot(sulfur.hist %>% filter(Year >= 1990),
                         aes(x=Year, y=value, color=Variable)) +
  geom_line(linewidth=1.5) +
  geom_line(data = sulfur.scens.ar6.newCEDSso2 %>% filter(Year>=2015,Year<=2050),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "grey",
            linetype = "solid", alpha = 0.1) +
  geom_line(data = sulfur.scens.ar6.newCEDSso2 %>% filter(Year>=2015,Year<=2050) %>%
              left_join(ar6.metadata) %>%
              filter(Category=="C1"),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "dodgerblue",
            linetype = "solid", alpha = 0.1) +
  geom_textline(data = sulfur.scens.cmip6 %>% filter(Year>=2015,Year<=2050),
                aes(x=Year, y=value, group=interaction(Model,Scenario), label = Scenario),
                linetype = "dashed",
                colour = "black",
                hjust=0.9) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c("blue", "red")) +
  labs(
    title = "Historical sulfur emissions",
    subtitle = "Grey: harmonized emissions AR6,\nLight blue: C1 scenarios",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.scens.newCEDSso2

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_newCEDSso2.pdf"),
       plot = p.sulfur.scens.newCEDSso2, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_newCEDSso2.png"),
       plot = p.sulfur.scens.newCEDSso2,
       width = 300, height = 200, dpi = 300, units = "mm")



### new harmonized emissions (updated CEDS sulfur + reduce_ratio_2040) ---------
sulfur.scens.cmip6.method2040 <- cmip6.emssions %>%
  filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, CMIP6)")
sulfur.scens.ar6.newCEDSso2.method2040 <- ar6.inf.emssions.newCEDSso2.method2040 %>%
  filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, with updated 2015 CEDS + reduce_ratio_2040)")

p.sulfur.scens.newCEDSso2.method2040 <- ggplot(sulfur.hist %>% filter(Year >= 1990),
                                    aes(x=Year, y=value, color=Variable)) +
  geom_line(linewidth=1.5) +
  geom_line(data = sulfur.scens.ar6.newCEDSso2 %>% filter(Year>=2015,Year<=2050),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "grey",
            linetype = "solid", alpha = 0.1) +
  geom_line(data = sulfur.scens.ar6.newCEDSso2 %>% filter(Year>=2015,Year<=2050) %>%
              left_join(ar6.metadata) %>%
              filter(Category=="C1"),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "dodgerblue",
            linetype = "solid", alpha = 0.1) +
  geom_textline(data = sulfur.scens.cmip6 %>% filter(Year>=2015,Year<=2050),
                aes(x=Year, y=value, group=interaction(Model,Scenario), label = Scenario),
                linetype = "dashed",
                colour = "black",
                hjust=0.9) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c("blue", "red")) +
  labs(
    title = "Historical sulfur emissions",
    subtitle = "Grey: harmonized emissions AR6,\nLight blue: C1 scenarios",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.scens.newCEDSso2.method2040

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_newCEDSso2_method2040.pdf"),
       plot = p.sulfur.scens.newCEDSso2.method2040, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_newCEDSso2_method2040.png"),
       plot = p.sulfur.scens.newCEDSso2.method2040,
       width = 300, height = 200, dpi = 300, units = "mm")




# Comparing methods ------------------------------------------------------------

# input emissions:
ar6.input.emissions.sulfur <- ar6.data.emissions %>%
  filter(Variable=="Emissions|Sulfur") %>%
  mutate(Variable = "Emissions|Sulfur (AR6 input)") %>%
  iamc_wide_to_long() %>%
  rename(Year=year)

# harmonization options:
sulfur.scens.ar6
sulfur.scens.ar6.newCEDSso2
sulfur.scens.ar6.newCEDSso2.method2040

# only where we have the data
scens.compare <- sulfur.scens.ar6.newCEDSso2.method2040 %>%
  distinct(Model, Scenario) %>%
  mutate(keep="true")

sulfur.compare.methods.long <- ar6.input.emissions.sulfur %>% # AR6 input emissions
  bind_rows(sulfur.scens.ar6 %>%
              mutate(Variable="Harmonized: AR6 default")) %>% # default AR6 harmonized emissions
  bind_rows(sulfur.scens.ar6.newCEDSso2 %>%
              mutate(Variable="Harmonized: Updated CEDS 2015")) %>% # updated CEDS 2015 harmonized emissions
  bind_rows(sulfur.scens.ar6.newCEDSso2.method2040 %>%
              mutate(Variable="Harmonized: Updated CEDS 2015 + reduce_ratio_2040"))  # updated CEDS 2015 harmonized emissions + reduce_ratio_2040
sulfur.compare.methods.wide <- sulfur.compare.methods.long %>%
  left_join(scens.compare) %>% filter(keep=="true") %>% select(-keep) %>%
  distinct() %>%
  pivot_wider(
    names_from = Variable,
    values_from = value
  )
sulfur.compare.methods.wide %>% View()

### Absolute values - emissions pathways ---------------------------------------
##### Until 2100 ---------------------------------------------------------------
p.sulfur.compare.methods.abs.until2100 <- ggplot(sulfur.compare.methods.long %>%
                                         filter(grepl(x=Scenario,
                                                      pattern="NGFS2",
                                                      fixed=T)),
                                   aes(x=Year,y=value, linetype = Model)) +
  facet_grid(~Variable) +
  geom_line(data = sulfur.compare.methods.long %>% filter(
    Variable=="Emissions|Sulfur (AR6 input)",
  ) %>%
              filter(grepl(x=Scenario,
                           pattern="NGFS2",
                           fixed=T)) %>% drop_na() %>% select(-Variable),
            aes(group=interaction(Model,Scenario)),
            alpha=0.3) +
  geom_line(aes(color=Variable,
                group=interaction(Model,Scenario)),
            alpha=1) +
  scale_color_manual(values = c("black","grey","pink", "purple"),
                     breaks = c("Emissions|Sulfur (AR6 input)",
                                "Harmonized: AR6 default",
                                "Harmonized: Updated CEDS 2015",
                                "Harmonized: Updated CEDS 2015 + reduce_ratio_2040")) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Comparing harmonization methods for sulfur emissions",
    subtitle = "Using NGFS2 scenarios from AR6 database.\nThree options: until 2100",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.compare.methods.abs.until2100

ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_abs_2100.pdf"),
       plot = p.sulfur.compare.methods.abs.until2100, device = cairo_pdf,
       width = 400, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_abs_2100.png"),
       plot = p.sulfur.compare.methods.abs.until2100,
       width = 400, height = 200, dpi = 300, units = "mm")

##### Until 2050 ---------------------------------------------------------------
p.sulfur.compare.methods.abs.until2050 <- ggplot(sulfur.compare.methods.long %>%
                                                   filter(grepl(x=Scenario,
                                                                pattern="NGFS2",
                                                                fixed=T),
                                                          Year<=2050),
                                                 aes(x=Year,y=value, linetype = Model)) +
  facet_grid(~Variable) +
  geom_line(data = sulfur.compare.methods.long %>% filter(
    Variable=="Emissions|Sulfur (AR6 input)",
  ) %>%
    filter(grepl(x=Scenario,
                 pattern="NGFS2",
                 fixed=T),
           Year<=2050) %>% drop_na() %>% select(-Variable),
  aes(group=interaction(Model,Scenario)),
  alpha=0.3) +
  geom_line(aes(color=Variable,
                group=interaction(Model,Scenario)),
            alpha=1) +
  scale_color_manual(values = c("black","grey","pink", "purple"),
                     breaks = c("Emissions|Sulfur (AR6 input)",
                                "Harmonized: AR6 default",
                                "Harmonized: Updated CEDS 2015",
                                "Harmonized: Updated CEDS 2015 + reduce_ratio_2040")) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Comparing harmonization methods for sulfur emissions",
    subtitle = "Using NGFS2 scenarios from AR6 database.\nThree options: until 2050",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.compare.methods.abs.until2050

ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_abs_2050.pdf"),
       plot = p.sulfur.compare.methods.abs.until2050, device = cairo_pdf,
       width = 400, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_abs_2050.png"),
       plot = p.sulfur.compare.methods.abs.until2050,
       width = 400, height = 200, dpi = 300, units = "mm")


### Differences - effect of harmonization --------------------------------------
sulfur.compare.methods.effect.wide <- sulfur.compare.methods.wide %>%
  mutate(`AR6 default` = `Harmonized: AR6 default` - `Emissions|Sulfur (AR6 input)`) %>%
  mutate(`Updated CEDS 2015` = `Harmonized: Updated CEDS 2015` - `Emissions|Sulfur (AR6 input)`) %>%
  mutate(`Updated CEDS 2015 + reduce_ratio_2040` = `Harmonized: Updated CEDS 2015 + reduce_ratio_2040` - `Emissions|Sulfur (AR6 input)`)

sulfur.compare.methods.effect.long <- sulfur.compare.methods.effect.wide %>%
  select(-c("Emissions|Sulfur (AR6 input)",
            "Harmonized: AR6 default",
            "Harmonized: Updated CEDS 2015",
            "Harmonized: Updated CEDS 2015 + reduce_ratio_2040")) %>%
  pivot_longer(cols = `AR6 default`:`Updated CEDS 2015 + reduce_ratio_2040`,
               names_to = "Variable", values_to = "value")

##### Until 2100 ---------------------------------------------------------------
p.sulfur.compare.methods.diff.until2100 <- ggplot(sulfur.compare.methods.effect.long %>%
                                                   filter(grepl(x=Scenario,
                                                                pattern="NGFS2",
                                                                fixed=T)) %>% drop_na(),
                                                 aes(x=Year,y=value, linetype = Model)) +
  facet_grid(~Variable) +
  geom_line(aes(color=Variable,
                group=interaction(Model,Scenario)),
            alpha=1) +
  scale_color_manual(values = c("grey","pink", "purple"),
                     breaks = c("AR6 default",
                                "Updated CEDS 2015",
                                "Updated CEDS 2015 + reduce_ratio_2040")) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Comparing harmonization methods for sulfur emissions",
    subtitle = "Using NGFS2 scenarios from AR6 database.\nThree options: until 2100",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.compare.methods.diff.until2100

ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_diff_2100.pdf"),
       plot = p.sulfur.compare.methods.diff.until2100, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_diff_2100.png"),
       plot = p.sulfur.compare.methods.diff.until2100,
       width = 300, height = 200, dpi = 300, units = "mm")

##### Until 2050 ---------------------------------------------------------------
p.sulfur.compare.methods.diff.until2050 <- ggplot(sulfur.compare.methods.effect.long %>%
                                                    filter(grepl(x=Scenario,
                                                                 pattern="NGFS2",
                                                                 fixed=T),
                                                           Year<=2050) %>% drop_na(),
                                                  aes(x=Year,y=value, linetype = Model)) +
  # facet_grid(~Variable) +
  geom_line(aes(color=Variable,
                group=interaction(Model,Scenario,Variable)),
            alpha=1) +
  scale_color_manual(values = c("grey","pink", "purple"),
                     breaks = c("AR6 default",
                                "Updated CEDS 2015",
                                "Updated CEDS 2015 + reduce_ratio_2040")) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Comparing harmonization methods for sulfur emissions",
    subtitle = "Using NGFS2 scenarios from AR6 database.\nThree options: until 2050",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.compare.methods.diff.until2050

ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_diff_2050.pdf"),
       plot = p.sulfur.compare.methods.diff.until2050, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures",
                       "sulfur_emissions_harmonize_compare_diff_2050.png"),
       plot = p.sulfur.compare.methods.diff.until2050,
       width = 300, height = 200, dpi = 300, units = "mm")
