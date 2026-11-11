// FSecure-WSN NEW RECONSTRUCTION: ns-3 topology and LR-WPAN device generator.
// NOT the original authors' 2026 source or an on-air multi-hop performance model.
// The exported link-success values below are explicitly analytical SURROGATES;
// installing LR-WPAN devices does not make these outputs measured MAC traces.
//
// For a native ns-3 recent release with lr-wpan enabled:
//   cp ns3/fsecure_scenario_export.cc $NS3_ROOT/scratch/
//   cd $NS3_ROOT
//   ./ns3 run "scratch/fsecure_scenario_export --nodes=100 --run=1 --attack=blackhole --outDir=/absolute/output/path"
//
// Version/API compatibility should be compiled and verified in user's ns-3 tree.
#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/lr-wpan-module.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <string>
#include <vector>

using namespace ns3;

static double
LinkSuccessSurrogate(double d, double range, double txPower, double threshold,
                     double referenceLoss, double exponent, double scale)
{
    if (d > range) return 0.0;
    const double rxDbm = txPower-referenceLoss-10.0*exponent*std::log10(std::max(1.0,d));
    const double z = std::max(-60.0,std::min(60.0,(rxDbm-threshold)/scale));
    const double p = 1.0/(1.0+std::exp(-z));
    return std::max(0.02,std::min(0.995,p));
}

int main(int argc, char* argv[])
{
    uint32_t nodesCount = 100;
    uint32_t run = 1;
    uint32_t seed = 20261111;
    double side = 500.0;
    double range = 50.0;
    double sinkX = 250.0;
    double sinkY = 525.0;
    double attackFraction = 0.15;
    double txPowerDbm=0.0, rxThresholdDbm=-91.0, referenceLossDb=40.0;
    double logDistanceExponent=3.0, successScaleDb=3.5;
    std::string attack = "blackhole";
    std::string outDir = "fsecure_ns3_scenario";
    CommandLine cmd(__FILE__);
    cmd.AddValue("nodes", "Sensor nodes, excluding sink",nodesCount);
    cmd.AddValue("run", "ns-3 RNG run identifier",run);
    cmd.AddValue("seed", "ns-3 RNG seed identifier",seed);
    cmd.AddValue("side", "Square area side in meters",side);
    cmd.AddValue("range", "Nominal link range in meters",range);
    cmd.AddValue("sinkX", "Sink X coordinate in meters",sinkX);
    cmd.AddValue("sinkY", "Sink Y coordinate in meters",sinkY);
    cmd.AddValue("attack", "none/blackhole/selective/sybil_proxy",attack);
    cmd.AddValue("attackFraction", "Injected attacker fraction",attackFraction);
    cmd.AddValue("outDir", "Output directory",outDir);
    cmd.Parse(argc,argv);
    if(nodesCount==0 || nodesCount>50000 || side<=0 || range<=0) NS_FATAL_ERROR("Invalid network dimensions");
    if(attack!="none" && attack!="blackhole" && attack!="selective" && attack!="sybil_proxy")
        NS_FATAL_ERROR("Unknown attack class");
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);
    NodeContainer nodes;
    nodes.Create(nodesCount+1); // sink = nodesCount
    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(nodes);
    Ptr<UniformRandomVariable> uniformX = CreateObject<UniformRandomVariable>();
    Ptr<UniformRandomVariable> uniformY = CreateObject<UniformRandomVariable>();
    uniformX->SetAttribute("Min",DoubleValue(0.0)); uniformX->SetAttribute("Max",DoubleValue(side));
    uniformY->SetAttribute("Min",DoubleValue(0.0)); uniformY->SetAttribute("Max",DoubleValue(side));
    uniformX->SetStream(10); uniformY->SetStream(11);
    for(uint32_t i=0;i<nodesCount;i++)
        nodes.Get(i)->GetObject<MobilityModel>()->SetPosition(Vector(uniformX->GetValue(),uniformY->GetValue(),0));
    nodes.Get(nodesCount)->GetObject<MobilityModel>()->SetPosition(Vector(sinkX,sinkY,0));
    // Real ns-3 LR-WPAN devices are installed, but NO PHY/MAC data traffic is sent here.
    // All exported probabilities below are analytical estimates, not LR-WPAN measurements.
    LrWpanHelper lrWpan;
    lrWpan.AddPropagationLossModel("ns3::LogDistancePropagationLossModel",
                                  "Exponent",DoubleValue(logDistanceExponent),
                                  "ReferenceLoss",DoubleValue(referenceLossDb));
    NetDeviceContainer lrwpanDevices = lrWpan.Install(nodes);
    lrWpan.CreateAssociatedPan(lrwpanDevices, 0xBEEF);

    Ptr<UniformRandomVariable> attackerRng=CreateObject<UniformRandomVariable>();
    attackerRng->SetStream(20);
    std::set<uint32_t> malicious;
    if(attack!="none")
    {
        const uint32_t badCount=std::min(nodesCount,static_cast<uint32_t>(std::round(nodesCount*attackFraction)));
        while(malicious.size()<badCount)
            malicious.insert(static_cast<uint32_t>(attackerRng->GetInteger(0,nodesCount-1)));
    }
    std::filesystem::create_directories(outDir);
    std::ofstream pos(outDir+"/nodes.csv");
    std::ofstream links(outDir+"/edges.csv");
    std::ofstream provenance(outDir+"/ns3_export_metadata.json");
    if(!pos || !links || !provenance) NS_FATAL_ERROR("Cannot create output CSV/JSON files");
    pos << "node_id,x_m,y_m,is_sink,attack_type\n";
    links << "src,dst,distance_m,link_success_probability_surrogate,lqi_proxy_0_255,nominal_delay_ms_surrogate,link_predicted_pdr\n";
    pos << std::setprecision(12); links << std::setprecision(12);
    for(uint32_t i=0;i<=nodesCount;i++)
    {
        const Vector a=nodes.Get(i)->GetObject<MobilityModel>()->GetPosition();
        pos<<i<<","<<a.x<<","<<a.y<<","<<(i==nodesCount?1:0)<<","
           <<(malicious.count(i)?attack:"none")<<"\n";
    }
    uint32_t edgeCount=0;
    for(uint32_t i=0;i<nodesCount;i++)
    {
        const Vector a=nodes.Get(i)->GetObject<MobilityModel>()->GetPosition();
        for(uint32_t j=0;j<=nodesCount;j++)
        {
            if(j==i)continue;
            const Vector b=nodes.Get(j)->GetObject<MobilityModel>()->GetPosition();
            const double d=std::hypot(a.x-b.x,a.y-b.y);
            const double p=LinkSuccessSurrogate(d,range,txPowerDbm,rxThresholdDbm,
                                                 referenceLossDb,logDistanceExponent,successScaleDb);
            if(p<=0)continue;
            links<<i<<","<<j<<","<<d<<","<<p<<","<<static_cast<int>(std::round(p*255.))<<","<<2.5+d/200.<<","<<p<<"\n";
            edgeCount++;
        }
    }
    provenance << "{\"backend\":\"ns3_topology_and_lrwpan_devices_WITH_analytical_links\","
               <<"\"ns3_release\":\"READ_FROM_YOUR_BUILD\","
               <<"\"original_experiment\":false,\"native_lr_wpan_traffic_sent\":false,"
               <<"\"link_quality_is_synthetic_proxy\":true,\"seed\":"<<seed
               <<",\"run\":"<<run<<",\"nodes\":"<<nodesCount
               <<",\"attack\":\""<<attack<<"\",\"edges\":"<<edgeCount<<"}\n";
    Simulator::Destroy();
    std::cout << "Wrote " << (nodesCount+1) << " nodes and " << edgeCount << " directed analytical links to " << outDir << std::endl;
    return 0;
}
