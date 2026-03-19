import bpy
import random
import math
from mathutils import Vector

# --- 1. SETUP & CLEANUP ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 200
random.seed(42)

# Make the world pitch black so the colors pop
world = bpy.data.worlds.get("World")
if world and world.use_nodes:
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.0, 0.0, 0.0, 1.0) 

# --- 2. MATERIAL CREATION ---
def create_graph_material(name, start_color, end_color, start_strength=0.0, end_strength=10.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    
    # Animate Base Color
    bsdf.inputs['Base Color'].default_value = start_color
    bsdf.inputs['Base Color'].keyframe_insert(data_path="default_value", frame=1)
    bsdf.inputs['Base Color'].keyframe_insert(data_path="default_value", frame=40)
    bsdf.inputs['Base Color'].default_value = end_color
    bsdf.inputs['Base Color'].keyframe_insert(data_path="default_value", frame=90)
    
    # Animate Glow (Emission) using a try/except block for different Blender versions
    try:
        bsdf.inputs['Emission Color'].default_value = end_color 
        bsdf.inputs['Emission Strength'].default_value = start_strength
        bsdf.inputs['Emission Strength'].keyframe_insert(data_path="default_value", frame=40)
        bsdf.inputs['Emission Strength'].default_value = end_strength
        bsdf.inputs['Emission Strength'].keyframe_insert(data_path="default_value", frame=90)
    except KeyError:
        # Fallback for older Blender versions
        bsdf.inputs['Emission'].default_value = (end_color[0], end_color[1], end_color[2], start_strength)
        bsdf.inputs['Emission'].keyframe_insert(data_path="default_value", frame=40)
        bsdf.inputs['Emission'].default_value = (end_color[0], end_color[1], end_color[2], end_strength)
        bsdf.inputs['Emission'].keyframe_insert(data_path="default_value", frame=90)
    
    return mat

# --- 3. COLORS & MATERIALS ---
start_silver = Vector((0.5, 0.5, 0.5, 1.0)) 
vibrant_cyan = Vector((0.0, 0.9, 1.0, 1.0))
vibrant_magenta = Vector((1.0, 0.0, 0.9, 1.0))

mat_class_A = create_graph_material("Mat_ClassA", start_silver, vibrant_cyan, end_strength=10.0)
mat_class_B = create_graph_material("Mat_ClassB", start_silver, vibrant_magenta, end_strength=10.0)

mat_edge = bpy.data.materials.new(name="Mat_Edge")
mat_edge.use_nodes = True
mat_edge.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = Vector((0.8, 0.8, 0.8, 1.0))

# --- 4. GENERATE GRAPH DATA ---
num_nodes = 50
nodes_data = []

for _ in range(num_nodes):
    cls = random.randint(0, 1)
    start_pos = Vector((random.uniform(-6, 6), random.uniform(-6, 6), random.uniform(-6, 6)))
    
    if cls == 0:
        cluster_center = Vector((-10, 0, 0))
    else:
        cluster_center = Vector((10, 0, 0))
        
    end_pos = cluster_center + Vector((random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5)))
    nodes_data.append({'start': start_pos, 'end': end_pos, 'class': cls})

edges_data = set()
for i in range(len(nodes_data)):
    same_class_indices = [j for j, n in enumerate(nodes_data) if n['class'] == nodes_data[i]['class'] and j != i]
    if same_class_indices:
        connections = random.sample(same_class_indices, min(2, len(same_class_indices)))
        for c in connections:
            edges_data.add(tuple(sorted((i, c))))

for _ in range(15):
    idx_a = random.choice([i for i, n in enumerate(nodes_data) if n['class'] == 0])
    idx_b = random.choice([i for i, n in enumerate(nodes_data) if n['class'] == 1])
    edges_data.add(tuple(sorted((idx_a, idx_b))))

# --- 5. BUILD NODES ---
for i, data in enumerate(nodes_data):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=data['start'])
    node = bpy.context.object
    node.name = f"Node_{i}"
    node.data.materials.append(mat_class_A if data['class'] == 0 else mat_class_B)
    
    # Animate node moving from tangled graph to latent space cluster
    node.keyframe_insert(data_path="location", frame=1)
    node.keyframe_insert(data_path="location", frame=110)
    node.location = data['end']
    node.keyframe_insert(data_path="location", frame=160)

# --- 6. BUILD EDGES ---
for idx_a, idx_b in edges_data:
    p1 = nodes_data[idx_a]['start']
    p2 = nodes_data[idx_b]['start']
    
    dist = (p2 - p1).length
    midpoint = (p1 + p2) / 2
    
    bpy.context.scene.frame_set(1)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=dist, location=midpoint)
    edge = bpy.context.object
    edge.data.materials.append(mat_edge)
    
    direction = p2 - p1
    edge.rotation_mode = 'QUATERNION'
    edge.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction)
    edge.rotation_mode = 'XYZ'
    
    # Animate edges dissolving to 0 scale
    edge.keyframe_insert(data_path="scale", frame=90)
    edge.scale = (0, 0, 0)
    edge.keyframe_insert(data_path="scale", frame=105)

# --- 7. CINEMATIC CAMERA ---
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.location = (0, -25, 6)
camera.rotation_euler = (math.radians(82), 0, 0)
bpy.context.scene.camera = camera

# Camera pulls back to reveal the separation
camera.keyframe_insert(data_path="location", frame=1)
camera.keyframe_insert(data_path="location", frame=110)
camera.location.y = -40 
camera.keyframe_insert(data_path="location", frame=170)

# --- 8. LIGHTING & RENDER ENGINE ---
bpy.ops.object.light_add(type='AREA', location=(0, -5, 20))
bpy.context.object.data.energy = 5000 
bpy.context.object.data.shape = 'RECTANGLE'
bpy.context.object.data.size = 30

bpy.context.scene.render.engine = 'BLENDER_EEVEE'
try:
    bpy.context.scene.eevee.use_bloom = True
except AttributeError:
    pass

print("Script execution complete! Press Spacebar in Rendered View to play.") 