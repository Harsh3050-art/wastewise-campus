import json
from pathlib import Path


def idea(level, title, mats, steps, mins, safety=""):
    return {"level": level, "title": title, "materials_needed": mats, "steps": steps,
            "time_minutes": mins, "safety_note": safety}


def safe(item, material, rec, bin_, kws, ideas):
    return {"keywords": kws, "answer": {"item": item, "material": material, "recyclable": rec,
            "correct_bin": bin_, "reuse_safe": True, "disposal_note": "", "ideas": ideas}}


def unsafe(item, material, bin_, kws, note):
    return {"keywords": kws, "answer": {"item": item, "material": material, "recyclable": False,
            "correct_bin": bin_, "reuse_safe": False, "disposal_note": note, "ideas": []}}


D = {}
# --- items that must NOT be reused: only disposal advice (checked first)
D["battery"] = unsafe("battery", "metal and chemicals", "ewaste", ["battery", "batteries", "power bank"],
    "Batteries are special care waste. Put them in the e-waste or hazardous bin, never in the wet or dry bin. Do not puncture, burn or open them.")
D["medicine"] = unsafe("medicine", "mixed", "hazardous", ["medicine", "medicines", "tablet", "tablets", "pills", "syrup", "expired medicine"],
    "Medicines are special care waste. Put them in the hazardous bin, never in the wet or dry bin, and never reuse the packaging for food.")
D["bulb"] = unsafe("bulb or tube light", "glass and metal", "hazardous", ["bulb", "tube light", "tubelight", "cfl"],
    "Bulbs and tube lights are special care waste. Keep them unbroken and put them in the hazardous bin.")
D["electronics"] = unsafe("electronic item", "plastic, metal and circuits", "ewaste",
    ["charger", "cable", "earphone", "earphones", "headphone", "headphones", "electronic", "electronics", "e-waste", "ewaste", "mobile", "phone"],
    "Electronic items are e-waste. Put them in the e-waste bin, never in the wet or dry bin. Do not open or burn them.")

# --- items with reuse ideas (order matters: the first match wins)
D["glass jar"] = safe("glass jar", "glass", True, "recyclable", ["glass jar", "jar", "glass bottle", "glass", "drinking glass"], [
    idea("easy", "Storage jar for snacks or stationery", ["glass jar", "warm soapy water"],
         ["Soak the jar in warm soapy water and peel off the label.", "Wash and dry it fully.", "Use it to store snacks, pens or clips."], 10,
         "Do not use a jar that has cracks or chipped edges."),
    idea("medium", "Desk lantern with an LED tea light", ["glass jar", "LED tea light", "ribbon or string"],
         ["Clean and dry the jar.", "Tie ribbon or string around the neck.", "Place an LED tea light inside."], 20,
         "Use LED lights only, never real candles near paper."),
    idea("creative", "Mini terrarium", ["wide jar", "small stones", "soil", "a small plant"],
         ["Add a layer of small stones at the bottom.", "Add soil on top.", "Plant a small succulent and water lightly."], 45,
         "Wash your hands after handling soil.")])
D["paper cup"] = safe("paper cup", "paper with a thin plastic lining", False, "dry", ["paper cup", "disposable cup", "cup", "tea cup"], [
    idea("easy", "Seedling pot", ["clean paper cup", "pencil", "soil", "seeds"],
         ["Rinse and dry the cup.", "Poke two small drainage holes in the bottom with a pencil.", "Fill with soil and plant a few seeds."], 10, ""),
    idea("medium", "Desk organiser set", ["3 or 4 paper cups", "glue", "coloured paper"],
         ["Cover each cup with coloured paper.", "Glue the cups side by side.", "Use them for pens, clips and erasers."], 25, ""),
    idea("creative", "Hanging paper-cup planters", ["4 paper cups", "string", "soil", "small plants"],
         ["Punch two holes near the rim of each cup.", "Tie string through the holes.", "Fill with soil, plant, and hang near a window."], 40,
         "Hang them from a strong hook.")])
D["notebook"] = safe("used notebook", "paper", True, "recyclable", ["notebook", "copy", "copies", "exercise book", "old notebook"], [
    idea("easy", "Rough-work pad", ["old notebook", "stapler or clip"],
         ["Tear out the unused pages.", "Stack them and clip or staple at the top.", "Use the pad for rough work and notes."], 5, ""),
    idea("medium", "Sticky-note style memo pad", ["unused pages", "scissors", "glue"],
         ["Cut the pages into small squares.", "Stack them and glue along one edge.", "Keep the pad on your desk."], 20,
         "Use scissors, and cut away from your hands."),
    idea("creative", "Handmade journal", ["old cover", "unused pages", "string", "thick needle"],
         ["Collect the clean pages into a bundle.", "Fold them in half and punch holes along the fold.", "Tie the bundle together with string."], 40,
         "Be careful with the needle.")])
D["newspaper"] = safe("newspaper", "paper", True, "recyclable", ["newspaper", "magazine", "paper", "waste paper"], [
    idea("easy", "Gift wrap and shelf liner", ["newspaper sheets", "tape"],
         ["Pick clean, dry sheets.", "Wrap gifts or line shelves and drawers with them.", "Secure with tape."], 5),
    idea("medium", "Paper bags", ["newspaper", "glue or tape", "scissors"],
         ["Fold a few sheets into a tube and glue the side.", "Fold the bottom flat and glue it.", "Add a paper strip as a handle."], 25),
    idea("creative", "Paper-mache bowl", ["newspaper strips", "flour", "water", "an old bowl", "plastic wrap"],
         ["Mix flour and water into a thin paste.", "Cover an upside-down bowl with plastic wrap and layer paste-dipped strips on it.", "Let it dry fully, then peel it off and paint it."], 60,
         "Let it dry completely before using it.")])
D["cardboard box"] = safe("cardboard box", "cardboard", True, "recyclable", ["cardboard", "carton", "box"], [
    idea("easy", "Drawer organiser", ["small cardboard box", "scissors"],
         ["Cut the box down so it fits your drawer.", "Cut a few strips for dividers.", "Place the dividers inside and sort your small items."], 10,
         "Cut away from your hands."),
    idea("medium", "Desk file holder", ["cereal-style box", "scissors", "paper or paint"],
         ["Cut the box diagonally from the top corners to the middle.", "Trim the edges neatly.", "Cover it with paper or paint it."], 30,
         "Cut away from your hands."),
    idea("creative", "Mini shelf for your room", ["2 or 3 boxes", "glue", "paper or paint"],
         ["Stack and glue the boxes with the open sides facing out.", "Let the glue dry fully.", "Cover or paint the boxes."], 60,
         "Only keep light items on it.")])
D["plastic bag"] = safe("plastic bag", "polythene", False, "dry", ["plastic bag", "carry bag", "polythene", "bag"], [
    idea("easy", "Dustbin liner or shoe cover", ["clean plastic bag"],
         ["Shake out any dirt.", "Use it as a small dustbin liner or to wrap muddy shoes.", "Keep a few folded in your bag."], 2),
    idea("medium", "Carry-bag holder", ["plastic bags", "an empty tissue box"],
         ["Fold each bag into a small triangle.", "Push the triangles into the tissue box.", "Pull them out one at a time when needed."], 15),
    idea("creative", "Woven plastic mat", ["10 to 15 plastic bags", "scissors"],
         ["Cut the bags into long loops.", "Link the loops together into a long strip.", "Braid or coil the strip into a small mat."], 90,
         "Keep it away from heat and flames.")])
D["plastic bottle"] = safe("plastic bottle", "PET plastic", True, "recyclable", ["plastic bottle", "pet bottle", "water bottle", "bottle"], [
    idea("easy", "Pen and pencil stand", ["empty bottle", "scissors", "tape"],
         ["Rinse the bottle and let it dry.", "Cut off the top third with scissors.", "Cover the cut edge with tape."], 10,
         "Cut slowly and cover the sharp edge with tape."),
    idea("medium", "Self-watering herb planter", ["bottle", "scissors", "cotton string", "soil", "seeds"],
         ["Cut the bottle in half.", "Make a small hole in the cap and thread the string through it.", "Turn the top half upside down into the bottom half.", "Fill the bottom with water and the top with soil, then plant."], 30,
         "Be careful while cutting plastic."),
    idea("creative", "Hanging vertical garden", ["3 or 4 bottles", "rope", "soil", "small plants"],
         ["Cut a window on the side of each bottle.", "Poke small drainage holes in the bottom.", "Tie the bottles in a line with rope and hang them on a balcony."], 90,
         "Hang it from a strong hook away from walkways.")])
D["old t-shirt"] = safe("old t-shirt", "cotton fabric", False, "dry", ["t-shirt", "tshirt", "t shirt", "shirt", "clothes", "cloth", "fabric", "old clothes"], [
    idea("easy", "Cleaning cloths", ["old t-shirt", "scissors"],
         ["Wash the t-shirt.", "Cut it into squares.", "Use the squares to dust or wipe surfaces."], 10,
         "Cut away from your hands."),
    idea("medium", "No-sew tote bag", ["old t-shirt", "scissors"],
         ["Cut off the sleeves and widen the neck opening.", "Cut 3 cm fringes along the bottom hem.", "Tie each front fringe to the matching back fringe."], 30,
         "Cut away from your hands."),
    idea("creative", "Braided coasters", ["old t-shirt", "scissors", "needle and thread"],
         ["Cut the shirt into long strips and stretch them.", "Braid three strips together.", "Coil the braid into a circle and stitch it in place."], 60,
         "Be careful with the needle.")])
D["tin can"] = safe("tin can", "steel or aluminium", True, "recyclable", ["tin can", "tin", "can", "aluminium can", "soda can", "steel can"], [
    idea("easy", "Pen holder", ["clean empty can", "tape or paper"],
         ["Wash the can and dry it.", "Cover the rim with tape so it is not sharp.", "Wrap the outside with paper and decorate."], 15,
         "Check that there are no sharp edges before use."),
    idea("medium", "Small plant pot", ["empty can", "nail and hammer", "soil", "a small plant"],
         ["Wash the can and cover the rim with tape.", "Make drainage holes in the bottom with a nail.", "Fill with soil and plant."], 30,
         "Ask for help with the hammer and nail."),
    idea("creative", "Pattern lantern", ["empty can", "water", "nail and hammer", "LED tea light"],
         ["Fill the can with water and freeze it.", "Tap a pattern of holes with a nail and hammer.", "Let the ice melt, dry the can, and put an LED tea light inside."], 60,
         "Use LED lights only, and ask for help with the hammer and nail.")])

Path("data").mkdir(exist_ok=True)
with open("data/fallback_ideas.json", "w", encoding="utf-8") as f:
    json.dump(D, f, indent=1, ensure_ascii=False)
print(len(D), "items written to data/fallback_ideas.json")