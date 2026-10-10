package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertNull;

public class TextUtil_truncate_Str_int_Test_Boundary_35 {


    @Test
    public void testTruncateWithNullStringReturnsNull() {
        String result = TextUtil.truncate(null, 10);
        assertNull(result, "truncate(null, 10) should return null for boundary null input");
    }

}
