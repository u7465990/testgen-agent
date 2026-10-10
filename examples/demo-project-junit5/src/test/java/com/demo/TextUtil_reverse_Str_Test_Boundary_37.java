package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TextUtil_reverse_Str_Test_Boundary_37 {


    @Test
    public void testReverseWithNullStringReturnsNull() {
        String s = null;
        String result = TextUtil.reverse(s);
        assertNull(result, "Reversing a null String should return null");
    }

}
