/**
 * Standalone Jimple extractor using SootUp 2.0+.
 *
 * Usage:
 *   javac -cp "sootup-core.jar;sootup-jimple-frontend.jar;..." SootUpExtractor.java
 *   java -cp "." SootUpExtractor <classpath> <className>
 *
 * Output: JSON lines — one per method.
 *   {"method":"<name>","signature":"<desc>","jimple":"<body>"}
 */
import java.io.*;
import java.util.*;
import sootup.core.*;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.model.*;
import sootup.core.types.*;
import sootup.core.util.Utils;
import sootup.core.views.View;
import sootup.java.bytecode.frontend.inputlocation.*;
import sootup.java.core.*;
import sootup.jimple.frontend.*;

public class SootUpExtractor {
    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: SootUpExtractor <classpath> <className>");
            System.exit(1);
        }
        String classpath = args[0];
        String className = args[1];

        // Create analysis input location from classpath
        AnalysisInputLocation inputLocation =
            new JavaClassPathAnalysisInputLocation(classpath);

        // Create view
        JavaView view = new JavaView(inputLocation);

        // Get class type
        ClassType classType = view.getIdentifierFactory().getClassType(className);
        Optional<? extends JavaClassType> classOpt = view.getClass(classType);
        if (!classOpt.isPresent()) {
            System.err.println("Class not found: " + className);
            System.exit(1);
        }

        JavaClassType clazz = classOpt.get();
        StringBuilder json = new StringBuilder();
        json.append("[");

        boolean first = true;
        for (SootMethod method : clazz.getMethods()) {
            if (!first) json.append(",");
            first = false;

            String methodName = method.getName();
            String signature = method.getSignature().toString();
            String jimpleBody = "";

            Optional<? extends Body> bodyOpt = method.getBody();
            if (bodyOpt.isPresent()) {
                jimpleBody = bodyOpt.get().toString();
            }

            json.append("{");
            json.append("\"method\":").append(JSON.quote(methodName)).append(",");
            json.append("\"signature\":").append(JSON.quote(signature)).append(",");
            json.append("\"jimple\":").append(JSON.quote(jimpleBody));
            json.append("}");
        }

        json.append("]");
        System.out.println(json.toString());
    }
}

/**
 * Minimal JSON string quoting utility (no external deps).
 */
class JSON {
    static String quote(String s) {
        if (s == null) return "\"\"";
        StringBuilder sb = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int)c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append("\"");
        return sb.toString();
    }
}
