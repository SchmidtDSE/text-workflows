# Blind reference labels, drafted with Claude (see DISCLOSURE.md), for label-sample.parquet (row order). site/taxon: sets of acceptable labels.
# crit: criteria labelled yes (a, c, i, n, q); all others in that list are no. None content = skip.
E, EC, NP, OO, G, N = "emperor_feature", "emperor_chain", "north_pacific", "other_ocean", "global", "none"
L = [
 (1,{G},"ai"[1:]+"n",{"plankton"}),(1,{G},"inq",{"none","plankton"}),(1,{G},"iq",{"none"}),(1,{G,NP},"in",{"plankton"}),
 (0,None,None,None),(1,{N},"",{"corals_sponges"}),(1,{NP},"",{"corals_sponges"}),(0,None,None,None),
 (1,{N},"",{"demersal"}),(1,{NP},"",{"demersal"}),(1,{E},"q",{"demersal"}),(1,{E},"",{"demersal"}),
 (1,{EC},"a",{"benthic_invertebrates","none"}),(1,{EC},"a",{"benthic_invertebrates","none"}),(1,{E},"an",{"benthic_invertebrates","none"}),(0,None,None,None),
 (1,{E,EC},"c",{"demersal"}),(1,{EC,N},"c",{"demersal"}),(1,{N},"c",{"demersal"}),(1,{N},"",{"demersal"}),
 (1,{OO},"n",{"none"}),(1,{G},"n",{"none","plankton"}),(0,None,None,None),(1,{NP},"n",{"none","plankton"}),
 (1,{EC,NP},"",{"none"}),(1,{G},"",{"none"}),(1,{EC,NP},"",{"corals_sponges"}),(1,{E},"n",{"none"}),
 (1,{NP},"",{"benthic_invertebrates"}),(1,{E},"",{"benthic_invertebrates"}),(1,{E},"",{"benthic_invertebrates"}),(1,{E},"",{"benthic_invertebrates"}),
 (1,{E},"n",{"microbes"}),(1,{N,EC},"",{"microbes"}),(1,{EC,N},"",{"microbes"}),(1,{N,NP},"",{"microbes","plankton"}),
 (1,{EC},"cin",{"seabirds"}),(1,{NP},"ciq",{"seabirds"}),(1,{NP,EC},"",{"seabirds"}),(1,{N},"",{"seabirds"}),
 (None,{OO,N},"",{"mesopelagic"}),(1,{OO,N},"n",{"mesopelagic"}),(1,{OO},"n",{"mesopelagic"}),(1,{N,OO},"",{"mesopelagic"}),
 (1,{EC,N},"",{"benthic_invertebrates","corals_sponges","none"}),(1,{G},"",{"benthic_invertebrates","none"}),(1,{E},"a",{"corals_sponges"}),(1,{N,G},"",{"benthic_invertebrates","none"}),
]
