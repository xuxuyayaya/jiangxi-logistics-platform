/* Curated real photographs; physical subject matches the business category. */
const mediaLibrary={
  "port-terminal": {
    "path": "/static/assets/logistics/port-terminal.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Container-Terminal_Bremerhaven_04.jpg",
    "artist": "H. Zell",
    "license": "CC BY-SA 3.0",
    "alt": "港口码头设施"
  },
  "freight-train": {
    "path": "/static/assets/logistics/freight-train.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:DB_Cargo_freight_train_at_Hedehusene_Station_08.jpg",
    "artist": "Leif Jørgensen",
    "license": "CC BY-SA 4.0",
    "alt": "铁路货运列车"
  },
  "cold-warehouse": {
    "path": "/static/assets/logistics/cold-warehouse.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Automatisches_Kleinteilelager_K%C3%BChllager.jpg",
    "artist": "Gilgen Logistics AG",
    "license": "CC BY-SA 4.0",
    "alt": "冷藏仓储设施"
  },
  "freight-truck": {
    "path": "/static/assets/library/road-truck.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Volvo_Truck_FH-Semi-trailer_truck-01ASD.jpg",
    "artist": "Asurnipal",
    "license": "CC BY-SA 4.0",
    "title": "File:Volvo Truck FH-Semi-trailer truck-01ASD.jpg",
    "alt": "公路货运牵引车实景"
},
  "port-hero": {
    "path": "/static/assets/logistics/port-hero.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Container-Terminal_Bremerhaven_02.jpg",
    "artist": "H. Zell",
    "license": "CC BY-SA 3.0",
    "alt": "港口起重设备"
  },
  "gan-nan-orange": {
    "path": "/static/assets/scenes/gan-nan-orange.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:NAVEL_ORANGE.png",
    "artist": "ILikeMangos999",
    "license": "CC BY 4.0",
    "alt": "脐橙实物"
  },
  "nanfeng-tangerine": {
    "path": "/static/assets/scenes/nanfeng-tangerine.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Mandarin_Oranges_(Citrus_Reticulata).jpg",
    "artist": "Joe Ravi",
    "license": "CC BY-SA 3.0",
    "alt": "蜜桔同类柑橘"
  },
  "nankang-furniture": {
    "path": "/static/assets/scenes/nankang-furniture.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Sofa_MET_1999.396.jpg",
    "artist": "John Henry Belter",
    "license": "CC0",
    "alt": "同类业务参考照片"
  },
  "bulk-metals": {
    "path": "/static/assets/scenes/bulk-metals.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Copper_cathode_UMMCII_Uralelectromed.jpg",
    "artist": "Niklitov",
    "license": "CC BY-SA 4.0",
    "alt": "铜阴极产品"
  },
  "grain-oil": {
    "path": "/static/assets/scenes/grain-oil.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Rice_grains_(IRRI).jpg",
    "artist": "IRRI Images",
    "license": "CC BY 2.0",
    "alt": "大米实物"
  },
  "electronics-battery": {
    "path": "/static/assets/library/electronics.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Printed_Circuit_Board_2.jpg",
    "artist": "Balurbala",
    "license": "CC BY-SA 3.0",
    "title": "File:Printed Circuit Board 2.jpg",
    "alt": "电子元器件与印刷电路板实景"
},
  "warehouse": {
    "path": "/static/assets/library/warehouse.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Modern_warehouse_with_pallet_rack_storage_system.jpg",
    "artist": "Axisadman",
    "license": "CC BY-SA 3.0",
    "alt": "普通仓储货架与托盘"
  },
  "cold-truck": {
    "path": "/static/assets/library/refrigerated-truck.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:FAW_Jiefang_J6L_001.jpg",
    "artist": "Elizbeth smith",
    "license": "CC BY-SA 4.0",
    "title": "File:FAW Jiefang J6L 001.jpg",
    "alt": "带制冷机组的冷藏货车实景"
},
  "furniture": {
    "path": "/static/assets/library/furniture.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Showroom_Furniture_Tempat_Tidur_dan_Sofa_Modern.jpg",
    "artist": "OKINURPIHATINI",
    "license": "CC0",
    "alt": "现代家具展示"
  },
  "port": {
    "path": "/static/assets/library/port.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Shanghai-Yangshan-Port-Containers2013-01.JPG",
    "artist": "Bruno Corpet (Quoique)",
    "license": "CC BY-SA 3.0",
    "alt": "上海洋山港集装箱码头"
  },
  "handling": {
    "path": "/static/assets/library/handling.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Container_loading_with_forklift_at_warehouse_in_Thailand.jpg",
    "artist": "Goterrestrial",
    "license": "CC BY 4.0",
    "alt": "叉车装柜作业"
  },
  "silo": {
    "path": "/static/assets/library/silo.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Gifford,_IL_silo_and_grain_elevator.jpg",
    "artist": "TheTechnician27",
    "license": "CC0",
    "alt": "粮食仓储筒仓"
  }
};
function mediaFigure(key,cls=''){const p=mediaLibrary[key];if(!p)return '';return `<figure class="media-figure ${cls}"><img src="${esc(p.path)}" alt="${esc(p.alt)} · 同类场景参考" loading="lazy"><a class="media-credit" href="${esc(p.source)}" target="_blank" rel="noopener" title="${esc(p.artist+' · '+p.license+' · 查看原图与许可')}">参考照片 · ${esc(p.artist)} · ${esc(p.license)}</a></figure>`}
function mediaForResource(x){const type=String(x.mode||'');const isTransport=x.resourceCategory==='transport'||/运力|车队|货车|船舶/.test(type);if(!isTransport){if(x.coldChain||/冷/.test(type))return 'cold-warehouse';if(x.handlingEquipment?.length)return 'handling';if(/粮/.test(type+' '+(x.title||'')))return 'silo';return 'warehouse'}if(x.coldChain||/冷/.test(type))return 'cold-truck';const modes=(x.transportModes||[]).join(' ');if((x.transportModes||[]).length>1)return 'handling';if(/铁路/.test(modes||type))return 'freight-train';if(/水运|水路|船/.test(modes||type))return 'port';return 'freight-truck'}
