from nessie_api.models import Plugin, Action, plugin , Graph, Node, Edge, Attribute,GraphType
import json
import os



def visualise_graph_handler(action: Action, context) -> str:
    graph_data = action.payload
    #Ensure the payload has to_dict method, which is expected for Graph objects
    if not hasattr(graph_data, "to_dict") or not callable(getattr(graph_data, "to_dict")):
        print("Invalid graph data provided.")
        raise ValueError("Expected a Graph object as payload.")
    graph_dict = graph_data.to_dict()
    TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "simpleVisualiser.html")
    with open(TEMPLATE_PATH, "r") as f:
        template = f.read()
    graph_json = json.dumps(graph_dict)
    graph_name = graph_dict["name"].replace(" ", "-").lower()
    html_content = template.replace("__GRAPH_DATA__", graph_json)

    return html_content



@plugin(name="Visualiser Simple", verbose=False)
def neisse_graph_visualiser_simple_plugin():
    handlers = {
        "visualise_graph": visualise_graph_handler,
    }
    requires = []
    setup_requires = {}

    ret_dict = {
        "handlers": handlers,
        "requires": requires,
        "setup_requires": setup_requires,
    }
    return ret_dict

if __name__ == "__main__": 
    plugin_instance = neisse_graph_visualiser_simple_plugin()
    print(f"Plugin '{plugin_instance.name}' initialized with actions: {plugin_instance.provided_actions}")
    graph = Graph("Test Graph", graph_type=GraphType.DIRECTED)
    node_a = Node("A", attributes={"label": Attribute("label", "Node A")})
    node_b = Node("B", attributes={"label": Attribute("label", "Node B")})
    node_c = Node("C", attributes={"label": Attribute("label", "Node C")})
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)
    graph.add_edge(Edge("edge2",source=node_a, target=node_b))
    graph.add_edge(Edge("edge3",source=node_b, target=node_c))

    action = Action(name="visualise_graph", payload=graph)
    result = plugin_instance.handle(action, context={})
    graph_name = graph.name.replace(" ", "-").lower()
    #The result is svg context that is here going to be added to html block and saved as html file
    html_content =    """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0
        <title>Graph Visualisation</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
    </head>
    <body>
    <div id="graph-container" style="width: 100%; height: 100vh; overflow: hidden;">
        """ + result + """ 
        </div>
<script>
(function initPhysics() {

  function boot() {
    const svgEl = document.querySelector('#main_view');
    if (!svgEl || typeof d3 === 'undefined') return;

    const W = window.innerWidth  || 900;
    const H = window.innerHeight || 600;

    const parent = svgEl.parentElement || document.body;
    if (getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }

    const badge = document.createElement('div');
    badge.id = '_zb';
    Object.assign(badge.style, {
      position:      'absolute',
      bottom:        '14px',
      right:         '14px',
      background:    'rgba(15,23,42,0.88)',
      color:         '#93c5fd',
      fontFamily:    'monospace',
      fontSize:      '12px',
      fontWeight:    '600',
      padding:       '3px 10px',
      borderRadius:  '6px',
      border:        '1px solid rgba(59,130,246,0.25)',
      pointerEvents: 'none',
      opacity:       '0',
      transition:    'opacity 0.2s',
      zIndex:        '9999',
    });
    parent.appendChild(badge);

    let badgeTimer;
    function showBadge(txt) {
      badge.textContent = txt;
      badge.style.opacity = '1';
      clearTimeout(badgeTimer);
      badgeTimer = setTimeout(() => badge.style.opacity = '0', 1200);
    }

    let currentTransform = d3.zoomIdentity;

    const zoom = d3.zoom()
      .scaleExtent([0.1, 5])
      .filter(event => {
        if (event.type === 'wheel') return true;
        return !event.target.closest('[node]');
      })
      .on('zoom', event => {
        currentTransform = event.transform;
        d3.select('#nodes').attr('transform', event.transform);
        d3.select('#edges').attr('transform', event.transform);
        showBadge(Math.round(event.transform.k * 100) + '%');
      });

    d3.select(svgEl).call(zoom).on('dblclick.zoom', null);

    const nodeEls = Array.from(svgEl.querySelectorAll('[node]'));
    if (!nodeEls.length) {
      console.warn('graph-physics: no [node] elements found');
      return;
    }

    function readNode(el) {
      const tag = el.tagName.toLowerCase();

      if (tag === 'circle' || tag === 'ellipse') {
        const cx = parseFloat(el.getAttribute('cx') || 0);
        const cy = parseFloat(el.getAttribute('cy') || 0);
        const rx = parseFloat(el.getAttribute('rx') || el.getAttribute('r') || 10);
        const ry = parseFloat(el.getAttribute('ry') || el.getAttribute('r') || 10);
        return { el, tag, x: cx - rx, y: cy - ry, w: rx * 2, h: ry * 2, rx, ry };
      }

      if (tag === 'g') {
        const tf = el.getAttribute('transform') || '';
        const m  = tf.match(/translate\(\s*([^,)]+)[,\s]+([^)]+)\)/);
        const x  = m ? parseFloat(m[1]) : 0;
        const y  = m ? parseFloat(m[2]) : 0;
        let w = 20, h = 20;
        el.querySelectorAll('rect').forEach(r => {
          const rw = parseFloat(r.getAttribute('width'))  || 0;
          const rh = parseFloat(r.getAttribute('height')) || 0;
          if (rw * rh > w * h) { w = rw; h = rh; }
        });
        if (w === 20) {
          try { const bb = el.getBBox(); w = bb.width || 20; h = bb.height || 20; } catch(e) {}
        }
        return { el, tag, x, y, w, h };
      }

      const x = parseFloat(el.getAttribute('x') || 0);
      const y = parseFloat(el.getAttribute('y') || 0);
      const w = parseFloat(el.getAttribute('width')  || 20);
      const h = parseFloat(el.getAttribute('height') || 20);
      return { el, tag, x, y, w, h };
    }

    const nodes = nodeEls.map(readNode).filter(Boolean);
    if (!nodes.length) return;

    const links = Array.from(svgEl.querySelectorAll('line[data-source][data-target]'))
      .map(el => {
        const si = parseInt(el.getAttribute('data-source'), 10);
        const ti = parseInt(el.getAttribute('data-target'), 10);
        if (!nodes[si] || !nodes[ti] || si === ti) return null;
        return { el, source: si, target: ti };
      })
      .filter(Boolean);

    const ncx = n => (n.tag === 'circle' || n.tag === 'ellipse') ? n.x + n.rx : n.x + n.w / 2;
    const ncy = n => (n.tag === 'circle' || n.tag === 'ellipse') ? n.y + n.ry : n.y + n.h / 2;

    function nodeExit(n, ux, uy) {
      if (n.tag === 'circle' || n.tag === 'ellipse') {
        return { x: ncx(n) + ux * n.rx, y: ncy(n) + uy * n.ry };
      }
      const sx = ux ? (n.w / 2) / Math.abs(ux) : Infinity;
      const sy = uy ? (n.h / 2) / Math.abs(uy) : Infinity;
      const s  = Math.min(sx, sy);
      return { x: ncx(n) + ux * s, y: ncy(n) + uy * s };
    }

    function edgeEndpoints(s, t) {
      const dx  = ncx(t) - ncx(s);
      const dy  = ncy(t) - ncy(s);
      const len = Math.hypot(dx, dy);
      if (len < 1) return { x1: ncx(s), y1: ncy(s), x2: ncx(t), y2: ncy(t) };
      const ux = dx / len, uy = dy / len;
      const p1 = nodeExit(s,  ux,  uy);
      const p2 = nodeExit(t, -ux, -uy);
      return { x1: p1.x, y1: p1.y, x2: p2.x - ux * 3, y2: p2.y - uy * 3 };
    }

    const avgSize = nodes.reduce((s, n) => s + Math.max(n.w, n.h), 0) / nodes.length;

    const sim = d3.forceSimulation(nodes)
      .force('charge',  d3.forceManyBody().strength(-260).distanceMax(600))
      .force('collide', d3.forceCollide().radius(n => Math.max(n.w, n.h) * 0.6 + 12).strength(0.9))
      .force('link',    d3.forceLink(links).id((_, i) => i).distance(avgSize * 2.8).strength(0.25))
      .force('cx',      d3.forceX(W / 2).strength(0.05))
      .force('cy',      d3.forceY(H / 2).strength(0.05))
      .alphaDecay(0.022)
      .velocityDecay(0.4)
      .on('tick', tick);

    function tick() {
      nodes.forEach(n => {
        const { el, tag } = n;
        if (tag === 'circle' || tag === 'ellipse') {
          el.setAttribute('cx', ncx(n));
          el.setAttribute('cy', ncy(n));
        } else if (tag === 'g') {
          el.setAttribute('transform', `translate(${n.x},${n.y})`);
        } else {
          el.setAttribute('x', n.x);
          el.setAttribute('y', n.y);
        }
      });

      links.forEach(({ el, source: s, target: t }) => {
        const { x1, y1, x2, y2 } = edgeEndpoints(s, t);
        el.setAttribute('x1', x1); el.setAttribute('y1', y1);
        el.setAttribute('x2', x2); el.setAttribute('y2', y2);
      });
    }

    function clientToSVG(clientX, clientY) {
      const rect = svgEl.getBoundingClientRect();
      return {
        x: (clientX - rect.left - currentTransform.x) / currentTransform.k,
        y: (clientY - rect.top  - currentTransform.y) / currentTransform.k,
      };
    }

    const drag = d3.drag()
      .on('start', function(event) {
        event.sourceEvent.stopPropagation();
        const n = d3.select(this).datum();
        if (!event.active) sim.alphaTarget(0.3).restart();
        n.fx = n.x;
        n.fy = n.y;
        d3.select(this)
          .style('filter', 'drop-shadow(0 0 10px rgba(59,130,246,0.9))')
          .style('cursor', 'grabbing')
          .raise();
      })
      .on('drag', function(event) {
        const n   = d3.select(this).datum();
        const pos = clientToSVG(event.sourceEvent.clientX, event.sourceEvent.clientY);
        n.fx = pos.x - n.w / 2;
        n.fy = pos.y - n.h / 2;
      })
      .on('end', function(event) {
        const n = d3.select(this).datum();
        if (!event.active) sim.alphaTarget(0);
        n.fx = null;
        n.fy = null;
        d3.select(this).style('filter', '').style('cursor', 'grab');
      });

    nodes.forEach(n => {
      d3.select(n.el).datum(n).style('cursor', 'grab').call(drag);
    });

    sim.alpha(0.8).restart();
  }

  setTimeout(() => requestAnimationFrame(boot), 0);

})();
</script>
</body>
</html>
    """
    html_content = html_content.replace("__GRAPH_NAME__", graph_name)
    with open("graph_visualisation.html", "w") as f:
        f.write(html_content)
    